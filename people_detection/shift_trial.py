"""
CrowdShield - Adaptive Person/Head Detection & Tracking Pipeline
Detects and tracks people in a live video stream (CCTV/webcam) using YOLOv8n.
Automatically switches to a head-detection model when the crowd gets dense
enough that full-body boxes start overlapping/occluding each other, since
heads survive occlusion far better than full bodies in packed scenes.
Outputs structured JSON with bounding boxes, track IDs, and confidence scores.
"""

import cv2
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from ultralytics import YOLO

# ============================================================
# CONFIG - edit these for your setup
# ============================================================
PERSON_MODEL_PATH = "yolov8n.pt"          # COCO nano - full body, class 0 = person
HEAD_MODEL_PATH = "yolov8n-head.pt"       # SCUT-HEAD nano - class 0 = head
SOURCE = "testing/datasets/videos/v1.mp4"                          # 0 = default webcam, or RTSP URL string, or video file path
CONF_THRESHOLD = 0.35                      # based on your benchmark's avg confidence (~0.43) for v8n
IOU_THRESHOLD = 0.5
TRACKER_CONFIG = "bytetrack.yaml"          # ships with ultralytics, no extra install needed
IMG_SIZE = 640

# Hysteresis thresholds on OCCUPIED AREA RATIO (fraction of frame covered by
# person boxes), not raw count - this is resolution/framing independent, unlike
# a fixed headcount. These starting values are a reasonable guess, not measured -
# watch the logged occupied_area_ratio / avg_pairwise_overlap on your real
# camera footage for a few minutes and tune these to match what actually looks
# "packed" vs "sparse" in your scene.
SWITCH_TO_HEAD_ABOVE_DENSITY = 0.35    # switch to head mode once boxes cover >35% of frame
SWITCH_TO_PERSON_BELOW_DENSITY = 0.20  # switch back once coverage drops below 20%

OUTPUT_DIR = Path("./output")
LATEST_FRAME_JSON = OUTPUT_DIR / "latest_frame.json"   # overwritten every frame - for a dashboard/API to poll
SESSION_LOG_JSONL = OUTPUT_DIR / "session_log.jsonl"   # one JSON line per frame - full history

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD BOTH MODELS UP FRONT
# ============================================================
# Both stay loaded in memory the whole time - reloading a model from disk
# on every switch would add a multi-second stall each time the crowd
# crosses the threshold, which defeats the point of a "live" pipeline.
print(f"Loading person model: {PERSON_MODEL_PATH}")
person_model = YOLO(PERSON_MODEL_PATH)

print(f"Loading head model: {HEAD_MODEL_PATH}")
head_model = YOLO(HEAD_MODEL_PATH)

MODELS = {
    "person": {"model": person_model, "classes": [0], "label": "person"},
    "head": {"model": head_model, "classes": [0], "label": "head"},
}


# ============================================================
# BUILD FRAME JSON
# ============================================================
def box_iou(a, b):
    """IoU between two (x1, y1, x2, y2) boxes in the same coordinate space (normalized here)."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_w, inter_h = max(0.0, inter_x2 - inter_x1), max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area

    return inter_area / union if union > 0 else 0.0


def compute_density_metrics(norm_boxes):
    """
    norm_boxes: list of (x1, y1, x2, y2) tuples, normalized 0-1.
    occupied_area_ratio: sum of box areas / frame area. Can exceed 1.0 when boxes
        overlap heavily - that's intentional, higher overlap should push it higher.
    avg_pairwise_overlap: mean IoU across every pair of boxes - direct occlusion signal.
    """
    if not norm_boxes:
        return {"occupied_area_ratio": 0.0, "avg_pairwise_overlap": 0.0}

    occupied_area_ratio = sum(
        max(0.0, x2 - x1) * max(0.0, y2 - y1) for x1, y1, x2, y2 in norm_boxes
    )

    n = len(norm_boxes)
    if n < 2:
        avg_overlap = 0.0
    else:
        overlaps = [
            box_iou(norm_boxes[i], norm_boxes[j])
            for i in range(n) for j in range(i + 1, n)
        ]
        avg_overlap = sum(overlaps) / len(overlaps)

    return {
        "occupied_area_ratio": round(occupied_area_ratio, 4),
        "avg_pairwise_overlap": round(avg_overlap, 4)
    }


def build_frame_json(frame_id, frame_shape, result, fps, detection_mode):
    height, width = frame_shape[:2]
    detections = []

    boxes = result.boxes
    if boxes is not None and len(boxes) > 0:
        has_ids = boxes.id is not None
        ids = boxes.id.cpu().tolist() if has_ids else [None] * len(boxes)
        confs = boxes.conf.cpu().tolist()
        xyxy = boxes.xyxy.cpu().tolist()

        for track_id, conf, (x1, y1, x2, y2) in zip(ids, confs, xyxy):
            detections.append({
                "person_id": int(track_id) if track_id is not None else None,
                "confidence": round(float(conf), 3),
                "bbox": {
                    "x1": round(x1, 1), "y1": round(y1, 1),
                    "x2": round(x2, 1), "y2": round(y2, 1)
                },
                "bbox_normalized": {
                    "x1": round(x1 / width, 4), "y1": round(y1 / height, 4),
                    "x2": round(x2 / width, 4), "y2": round(y2 / height, 4)
                }
            })

    density = compute_density_metrics(
        [(d["bbox_normalized"]["x1"], d["bbox_normalized"]["y1"],
          d["bbox_normalized"]["x2"], d["bbox_normalized"]["y2"]) for d in detections]
    )

    return {
        "frame_id": frame_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_width": width,
        "frame_height": height,
        "processing_fps": round(fps, 2),
        "detection_mode": detection_mode,   # "person" or "head" - tells downstream code which box scale to expect
        "people_count": len(detections),
        "occupied_area_ratio": density["occupied_area_ratio"],
        "avg_pairwise_overlap": density["avg_pairwise_overlap"],
        "detections": detections
    }


# ============================================================
# MAIN LOOP
# ============================================================
def run():
    cap = cv2.VideoCapture(SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {SOURCE}")

    # ---------- Video Writer ----------
    fps_video = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    video_writer = cv2.VideoWriter(
        str(OUTPUT_DIR / "annotated_output.mp4"),
        fourcc,
        fps_video,
        (width, height)
    )
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {SOURCE}")

    frame_id = 0
    prev_time = time.time()
    current_mode = "person"   # start in normal person-detection mode

    print("Starting live detection. Press Ctrl+C to stop.")
    print(f"Will switch to head mode above {SWITCH_TO_HEAD_ABOVE_DENSITY:.0%} occupied area, "
          f"back to person mode below {SWITCH_TO_PERSON_BELOW_DENSITY:.0%}.")

    try:
        with open(SESSION_LOG_JSONL, "a") as log_file:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Stream ended or frame grab failed.")
                    break

                cfg = MODELS[current_mode]
                results = cfg["model"].track(
                    frame,
                    persist=True,
                    classes=cfg["classes"],
                    conf=CONF_THRESHOLD,
                    iou=IOU_THRESHOLD,
                    tracker=TRACKER_CONFIG,
                    imgsz=IMG_SIZE,
                    verbose=False
                )
                result = results[0]
                annotated_frame = result.plot()

                video_writer.write(annotated_frame)

                now = time.time()
                fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now

                frame_json = build_frame_json(frame_id, frame.shape, result, fps, current_mode)

                # overwrite latest snapshot - for a dashboard/API to poll live state
                with open(LATEST_FRAME_JSON, "w") as f:
                    json.dump(frame_json, f, indent=2)

                # append to permanent session log
                log_file.write(json.dumps(frame_json) + "\n")
                log_file.flush()

                print(f"Frame {frame_id:>6} | Mode: {current_mode:>6} | "
                      f"People: {frame_json['people_count']:>3} | "
                      f"Density: {frame_json['occupied_area_ratio']:.3f} | "
                      f"FPS: {frame_json['processing_fps']:>5.1f}")

                # decide the mode for the NEXT frame based on this frame's occupied area ratio
                density = frame_json["occupied_area_ratio"]
                if current_mode == "person" and density > SWITCH_TO_HEAD_ABOVE_DENSITY:
                    current_mode = "head"
                    print(f"  -> switching to HEAD mode (density {density:.3f} > {SWITCH_TO_HEAD_ABOVE_DENSITY})")
                elif current_mode == "head" and density < SWITCH_TO_PERSON_BELOW_DENSITY:
                    current_mode = "person"
                    print(f"  -> switching to PERSON mode (density {density:.3f} < {SWITCH_TO_PERSON_BELOW_DENSITY})")

                frame_id += 1

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        cap.release()
        video_writer.release()
        cv2.destroyAllWindows() 
        print(f"\nLatest frame JSON: {LATEST_FRAME_JSON}")
        print(f"Full session log:  {SESSION_LOG_JSONL}")


if __name__ == "__main__":
    run()