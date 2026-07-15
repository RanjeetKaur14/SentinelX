"""
adapter.py
----------
Bridges Stage 1 (people_detection / best.py) -> Stage 2 (crowd_analysis
AnalyticsEngine).

WHY THIS FILE EXISTS
=====================
best.py's `build_frame_json()` and crowd_analysis's `FrameInput.from_dict()`
speak two DIFFERENT JSON shapes. They were built by different people
against no shared contract, so the field names don't line up:

    people_detection output          crowd_analysis input (models.FrameInput)
    ------------------------         ----------------------------------------
    frame_id                    ->   frame
    timestamp (ISO-8601 string) ->   timestamp (float, epoch seconds)
    frame_width / frame_height  ->   image_size: {"width", "height"}
    (no camera id at all)       ->   camera_id (required)
    detections[].person_id      ->   (DROPPED - see note below)
    detections[].bbox            ->   detections[].bbox as [x1, y1, x2, y2]
        {"x1","y1","x2","y2"}          (crowd_analysis wants a tuple/list,
                                         not a dict)
    detections[].confidence     ->   detections[].confidence (same)

NOTE ON person_id / track_id:
crowd_analysis has its OWN centroid tracker (tracker.py) which assigns
its own `track_id`s from raw bounding boxes frame-to-frame. It does not
consume upstream track IDs at all -- so YOLO/ByteTrack's `person_id` is
intentionally discarded here. This is fine (crowd_analysis re-derives
its own consistent IDs), but it does mean the two trackers can disagree
slightly on identity during heavy occlusion. If that ever matters for
your accuracy numbers, the fix is on the crowd_analysis side (feed the
upstream ID in), not here.
"""

from datetime import datetime, timezone
from typing import Any, Dict


def detector_frame_to_analytics_input(
    detector_frame: Dict[str, Any],
    camera_id: str = "cam_01",
) -> Dict[str, Any]:
    """
    Convert one frame of people_detection output (best.py / crowd_detector.py
    `build_frame_json()` shape) into the dict `AnalyticsEngine.process_frame()`
    expects (models.FrameInput.from_dict() shape).
    """
    ts_raw = detector_frame["timestamp"]
    if isinstance(ts_raw, str):
        # best.py writes ISO-8601 UTC strings via datetime.now(timezone.utc).isoformat()
        timestamp = datetime.fromisoformat(ts_raw).timestamp()
    else:
        # already numeric (e.g. if you switch the detector to time.time())
        timestamp = float(ts_raw)

    detections = []
    for d in detector_frame.get("detections", []):
        bbox = d["bbox"]
        detections.append({
            "bbox": [bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]],
            "confidence": d["confidence"],
        })

    return {
        "frame": detector_frame["frame_id"],
        "timestamp": timestamp,
        "camera_id": camera_id,
        "image_size": {
            "width": detector_frame["frame_width"],
            "height": detector_frame["frame_height"],
        },
        "detections": detections,
    }
