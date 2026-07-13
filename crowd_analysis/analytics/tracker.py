from typing import Dict, List, Tuple
import numpy as np

from .config import TrackerConfig
from .models import Detection, Track, BBox, Point


def _iou(box_a: BBox, box_b: BBox) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


class CentroidTracker:
    def __init__(self, config: TrackerConfig):
        self._config = config
        self._tracks: Dict[int, Track] = {}
        self._next_id: int = 0

    @property
    def tracks(self) -> Dict[int, Track]:
        return self._tracks

    def _new_track_id(self) -> int:
        track_id = self._next_id
        self._next_id += 1
        return track_id

    def update(self, detections: List[Detection]) -> List[Track]:
        det_centroids = [d.centroid for d in detections]

        if not self._tracks:
            for det, centroid in zip(detections, det_centroids):
                self._spawn_track(det, centroid)
            return list(self._tracks.values())

        if not detections:
            self._age_all_tracks()
            return list(self._tracks.values())

        matched_track_ids, matched_det_idxs = self._greedy_match(
            detections, det_centroids
        )

        for track_id, det_idx in zip(matched_track_ids, matched_det_idxs):
            self._apply_match(track_id, detections[det_idx])

        # Handle unmatched existing tracks (aged out / possibly deleted).
        unmatched_track_ids = set(self._tracks.keys()) - set(matched_track_ids)
        for track_id in unmatched_track_ids:
            self._age_track(track_id)

        matched_det_set = set(matched_det_idxs)
        for idx, (det, centroid) in enumerate(zip(detections, det_centroids)):
            if idx not in matched_det_set:
                self._spawn_track(det, centroid)

        return list(self._tracks.values())

    def _greedy_match(
        self, detections: List[Detection], det_centroids: List[Point]
    ) -> Tuple[List[int], List[int]]:
        """
        Greedy assignment between existing tracks and new detections
        using a combined distance + IoU cost (see module docstring).

        Matching is anchored on each track's *predicted* centroid
        (constant-velocity one-frame extrapolation) rather than its
        last observed centroid, which meaningfully reduces ID switches
        for fast-moving crowds -- exactly the surge scenario this
        system needs to track reliably.
        """
        track_ids = list(self._tracks.keys())
        predicted_centroids = np.array(
            [self._tracks[tid].predicted_centroid for tid in track_ids],
            dtype=np.float64,
        )
        det_arr = np.array(det_centroids, dtype=np.float64)

        diff = predicted_centroids[:, None, :] - det_arr[None, :, :]
        dist_matrix = np.sqrt((diff ** 2).sum(axis=2))

        gate = self._config.max_match_distance
        norm_dist_matrix = dist_matrix / gate

        matched_track_ids: List[int] = []
        matched_det_idxs: List[int] = []

        available_rows = set(range(len(track_ids)))
        available_cols = set(range(len(det_centroids)))

        candidates = []
        for r in available_rows:
            track = self._tracks[track_ids[r]]
            for c in available_cols:
                dist = dist_matrix[r, c]
                if dist > gate:
                    continue
                iou = _iou(track.bbox, detections[c].bbox)
                if iou < self._config.min_iou_for_match:
                    continue
                cost = (
                    self._config.distance_weight * norm_dist_matrix[r, c]
                    + self._config.iou_weight * (1.0 - iou)
                )
                candidates.append((cost, r, c))

        candidates.sort(key=lambda x: x[0])

        for cost, r, c in candidates:
            if r not in available_rows or c not in available_cols:
                continue

            matched_track_ids.append(track_ids[r])
            matched_det_idxs.append(c)
            available_rows.discard(r)
            available_cols.discard(c)

        return matched_track_ids, matched_det_idxs

    def _spawn_track(self, det: Detection, centroid: Point) -> None:
        track_id = self._new_track_id()
        self._tracks[track_id] = Track(
            track_id=track_id,
            bbox=det.bbox,
            centroid=centroid,
            confidence=det.confidence,
            history=[],
            disappeared=0,
            age=1,
            velocity=(0.0, 0.0),
        )

    def _apply_match(self, track_id: int, det: Detection) -> None:
        track = self._tracks[track_id]
        new_centroid = det.centroid
        elapsed_frames = track.disappeared + 1
        track.velocity = (
            (new_centroid[0] - track.centroid[0]) / elapsed_frames,
            (new_centroid[1] - track.centroid[1]) / elapsed_frames,
        )
        track.bbox = det.bbox
        track.centroid = new_centroid
        track.confidence = det.confidence
        track.disappeared = 0
        track.age += 1

    def _age_track(self, track_id: int) -> None:
        track = self._tracks[track_id]
        track.disappeared += 1
        if track.disappeared > self._config.max_disappeared_frames:
            del self._tracks[track_id]

    def _age_all_tracks(self) -> None:
        for track_id in list(self._tracks.keys()):
            self._age_track(track_id)
