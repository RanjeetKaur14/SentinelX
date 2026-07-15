"""
models.py
---------
Typed data structures shared across the Crowd Analytics Engine.

Using dataclasses (instead of raw dicts) inside the engine gives us
static-analysis friendliness and cheap attribute access, while the
input/output boundary still speaks plain JSON-compatible dicts.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any


BBox = Tuple[float, float, float, float]  # (x1, y1, x2, y2)
Point = Tuple[float, float]               # (x, y)


@dataclass
class Detection:
    """A single raw detection as received from the upstream detector."""

    bbox: BBox
    confidence: float

    @property
    def centroid(self) -> Point:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass
class FrameInput:
    """Parsed representation of one incoming frame payload."""

    frame: int
    timestamp: float
    camera_id: str
    image_width: int
    image_height: int
    detections: List[Detection]

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "FrameInput":
        size = payload["image_size"]
        dets = [
            Detection(bbox=tuple(d["bbox"]), confidence=float(d["confidence"]))
            for d in payload.get("detections", [])
        ]
        return FrameInput(
            frame=int(payload["frame"]),
            timestamp=float(payload["timestamp"]),
            camera_id=str(payload["camera_id"]),
            image_width=int(size["width"]),
            image_height=int(size["height"]),
            detections=dets,
        )


@dataclass
class Track:
    """
    Persistent state for one tracked person.

    This object is mutated in-place, frame over frame, by the tracker
    and the trajectory module. It is intentionally *not* frozen.
    """

    track_id: int
    bbox: BBox
    centroid: Point
    confidence: float = 0.0

    # Ring buffer of past (timestamp, centroid) pairs, oldest first.
    # Bounded by TrajectoryConfig.history_length (enforced in
    # trajectory.py). Timestamps make speed robust to variable/dropped
    # frame rates on edge hardware.
    history: List[Tuple[float, Point]] = field(default_factory=list)

    # Number of consecutive frames this track has gone undetected.
    disappeared: int = 0

    # Total number of frames this track has been observed (matched).
    age: int = 0

    # Last observed per-frame displacement vector (dx, dy), used by
    # the tracker for constant-velocity centroid prediction. This is
    # NOT a Kalman filter -- just "where did it move last frame,
    # assume it keeps moving that way for one more frame" -- O(1),
    # no matrix math, no covariance tracking.
    velocity: Point = (0.0, 0.0)

    # Computed analytics (updated each frame by trajectory.py)
    instantaneous_speed: float = 0.0  # pixels/second
    average_speed: float = 0.0        # pixels/second
    direction: str = "Stationary"

    # Which side of each entry/exit line this track was last seen on.
    # Keyed by line name -> signed side (float). Used by entry_exit.py
    # to detect crossings without recomputing full history.
    last_line_side: Dict[str, float] = field(default_factory=dict)

    @property
    def predicted_centroid(self) -> Point:
        """
        Constant-velocity centroid estimate, used by the tracker as
        the matching anchor instead of the stale last centroid.

        Scales by `disappeared + 1` frames rather than always
        extrapolating a single frame ahead: a track that has been
        undetected for several frames needs its position projected
        forward by that many frames' worth of velocity (velocity is
        stored as a *per-frame* rate -- see tracker._apply_match's
        elapsed_frames division), or the prediction lags further and
        further behind a fast-moving track the longer it's occluded --
        which defeats the purpose of prediction for exactly the
        scenario it exists to help (a person briefly occluded while
        moving fast through a dense crowd). Falls back to the current
        centroid when velocity is zero (e.g. brand-new or stationary
        tracks).
        """
        steps = self.disappeared + 1
        return (
            self.centroid[0] + self.velocity[0] * steps,
            self.centroid[1] + self.velocity[1] * steps,
        )


@dataclass
class TrackUpdate:
    """Lightweight, JSON-serializable view of a track for output."""

    track_id: int
    centroid: Point
    speed: float
    direction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "centroid": [round(self.centroid[0], 2), round(self.centroid[1], 2)],
            "speed": round(self.speed, 3),
            "direction": self.direction,
        }


@dataclass
class FlowResult:
    """
    Richer flow-classification result. Replaces the old bare-string
    return from FlowClassifier.classify() -- the underlying stats
    (confidence, heading, entropy, per-direction counts) were already
    being computed internally (or trivially derivable) and discarded;
    this just exposes them as raw measurements. Note `direction_
    histogram` is a measurement, not an interpretation -- it's just
    "how many tracks are heading each way"; it deliberately does NOT
    compute things like reverse-flow percentage, which requires a
    judgment call about what counts as "opposing" and belongs to the
    downstream Risk Prediction Engine.
    """

    label: str                       # "Uniform" | "Mixed" | "Chaotic"
    confidence: float                # mean resultant length, 0..1
    dominant_heading: Optional[float]  # degrees, None if no moving tracks
    entropy: float                   # Shannon entropy over 8 compass bins
    direction_histogram: Dict[str, int]  # counts per compass direction + Stationary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": round(self.confidence, 3),
            "dominant_heading": (
                round(self.dominant_heading, 1)
                if self.dominant_heading is not None
                else None
            ),
            "entropy": round(self.entropy, 3),
            "direction_histogram": dict(self.direction_histogram),
        }


@dataclass
class EntryExitStats:
    """Raw entry/exit crossing counts, global and per named line."""

    total_entry: int
    total_exit: int
    per_line: Dict[str, Dict[str, int]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_entry": self.total_entry,
            "total_exit": self.total_exit,
            "per_line": {name: dict(stats) for name, stats in self.per_line.items()},
        }


@dataclass
class HeatmapBundle:
    """Raw dual-decay heatmap grids -- fast, slow, and their difference."""

    fast: List[List[float]]
    slow: List[List[float]]
    trend: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {"fast": self.fast, "slow": self.slow, "trend": self.trend}


@dataclass
class CrowdMetrics:
    """
    Derived, frame-level crowd metrics. Pure MEASUREMENT of what the
    other modules already compute -- this module answers "what is
    happening inside the crowd", never "is the crowd becoming
    dangerous". No congestion/risk/danger/stampede/alert concepts of
    any kind live here; that interpretation is exclusively the
    downstream Risk Prediction Engine's responsibility. Concretely,
    this means: no congestion index, no density gradient, no reverse-
    flow percentage, no stationary-cluster detection -- those require
    a judgment call about what the numbers *mean*. This module instead
    exposes the raw ingredients (normalized density, direction
    histogram, a plain list of stationary track IDs) so the Risk
    Engine can apply its own interpretation logic and thresholds.
    """

    people_count: int
    average_speed: float             # pixels/second, mean over active tracks
    occupancy_growth: float          # people_count delta over buffer window
    zone_growth: List[List[float]]   # per-cell density delta, same shape as heatmap
    density: Dict[str, int]
    normalized_density: Dict[str, float]
    flow: FlowResult
    stationary_tracks: List[int]     # track IDs currently classified Stationary
    entry_exit: EntryExitStats
    heatmap: HeatmapBundle

    def to_dict(self) -> Dict[str, Any]:
        return {
            "people_count": self.people_count,
            "average_speed": round(self.average_speed, 3),
            "occupancy_growth": round(self.occupancy_growth, 3),
            "zone_growth": self.zone_growth,
            "density": self.density,
            "normalized_density": {
                k: round(v, 6) for k, v in self.normalized_density.items()
            },
            "flow": self.flow.to_dict(),
            "stationary_tracks": list(self.stationary_tracks),
            "entry_exit": self.entry_exit.to_dict(),
            "heatmap": self.heatmap.to_dict(),
        }


@dataclass
class FrameAnalytics:
    """
    Full analytics result for a single processed frame.

    NOTE: output shape changed from v1 (flat people_count/density/
    heatmap/flow fields) to a nested `crowd_metrics` block. This is a
    deliberate, requested breaking change to the JSON contract -- see
    migration notes. `frame` and `tracks` remain top-level since the
    downstream Risk Prediction Engine and Dashboard need those first.
    """

    frame: int
    tracks: List[TrackUpdate]
    crowd_metrics: CrowdMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.frame,
            "tracks": [t.to_dict() for t in self.tracks],
            "crowd_metrics": self.crowd_metrics.to_dict(),
        }
