import cv2
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from ultralytics import YOLO

PERSON_MODEL_PATH = "yolov8n.pt"          
HEAD_MODEL_PATH = "yolov8n-head.pt"       
SOURCE = "testing/datasets/videos/v1.mp4"                       
CONF_THRESHOLD = 0.35                   
IOU_THRESHOLD = 0.5
TRACKER_CONFIG = "bytetrack.yaml"         
IMG_SIZE = 640

SWITCH_TO_HEAD_ABOVE_DENSITY = 0.35   
SWITCH_TO_PERSON_BELOW_DENSITY = 0.20 

OUTPUT_DIR = Path("./output")
LATEST_FRAME_JSON = OUTPUT_DIR / "latest_frame.json"   
SESSION_LOG_JSONL = OUTPUT_DIR / "session_log.jsonl"  

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Loading person model: {PERSON_MODEL_PATH}")
person_model = YOLO(PERSON_MODEL_PATH)

print(f"Loading head model: {HEAD_MODEL_PATH}")
head_model = YOLO(HEAD_MODEL_PATH)

MODELS = {
    "person": {"model": person_model, "classes": [0], "label": "person"},
    "head": {"model": head_model, "classes": [0], "label": "head"},
}

def box_iou(a, b):
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
        "detection_mode": detection_mode,  
        "people_count": len(detections),
        "occupied_area_ratio": density["occupied_area_ratio"],
        "avg_pairwise_overlap": density["avg_pairwise_overlap"],
        "detections": detections
    }

def run():
    cap = cv2.VideoCapture(SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {SOURCE}")

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
    current_mode = "person"  

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

                with open(LATEST_FRAME_JSON, "w") as f:
                    json.dump(frame_json, f, indent=2)

                log_file.write(json.dumps(frame_json) + "\n")
                log_file.flush()

                print(f"Frame {frame_id:>6} | Mode: {current_mode:>6} | "
                      f"People: {frame_json['people_count']:>3} | "
                      f"Density: {frame_json['occupied_area_ratio']:.3f} | "
                      f"FPS: {frame_json['processing_fps']:>5.1f}")

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
