from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any

BBox = Tuple[float, float, float, float] 
Point = Tuple[float, float]               

@dataclass
class Detection:
    bbox: BBox
    confidence: float

    @property
    def centroid(self) -> Point:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass
class FrameInput:
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

    track_id: int
    bbox: BBox
    centroid: Point
    confidence: float = 0.0
    history: List[Tuple[float, Point]] = field(default_factory=list)
    disappeared: int = 0
    age: int = 0

    velocity: Point = (0.0, 0.0)

    instantaneous_speed: float = 0.0 
    average_speed: float = 0.0     
    direction: str = "Stationary"
    last_line_side: Dict[str, float] = field(default_factory=dict)

    @property
    def predicted_centroid(self) -> Point:
        
        steps = self.disappeared + 1
        return (
            self.centroid[0] + self.velocity[0] * steps,
            self.centroid[1] + self.velocity[1] * steps,
        )


@dataclass
class TrackUpdate:

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

    label: str                       
    confidence: float                
    dominant_heading: Optional[float]  
    entropy: float                   
    direction_histogram: Dict[str, int]  

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

    fast: List[List[float]]
    slow: List[List[float]]
    trend: List[List[float]]

    def to_dict(self) -> Dict[str, Any]:
        return {"fast": self.fast, "slow": self.slow, "trend": self.trend}


@dataclass
class CrowdMetrics:
    people_count: int
    average_speed: float            
    occupancy_growth: float          
    zone_growth: List[List[float]]   
    density: Dict[str, int]
    normalized_density: Dict[str, float]
    flow: FlowResult
    stationary_tracks: List[int]    
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

    frame: int
    tracks: List[TrackUpdate]
    crowd_metrics: CrowdMetrics

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.frame,
            "tracks": [t.to_dict() for t in self.tracks],
            "crowd_metrics": self.crowd_metrics.to_dict(),
        }
