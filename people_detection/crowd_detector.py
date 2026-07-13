
import cv2
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = "yolov8n.pt"          
SOURCE = "testing/datasets/videos/v1.mp4"                  
CONF_THRESHOLD = 0.35               
IOU_THRESHOLD = 0.5
TRACKER_CONFIG = "bytetrack.yaml"     
IMG_SIZE = 640

OUTPUT_DIR = Path("./output")
LATEST_FRAME_JSON = OUTPUT_DIR / "latest_frame.json"  
SESSION_LOG_JSONL = OUTPUT_DIR / "session_log.jsonl"   

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Loading model: {MODEL_PATH}")
model = YOLO(MODEL_PATH)
def build_frame_json(frame_id, frame_shape, result, fps):
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

    return {
        "frame_id": frame_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "frame_width": width,
        "frame_height": height,
        "processing_fps": round(fps, 2),
        "people_count": len(detections),
        "detections": detections
    }

def run():
    cap = cv2.VideoCapture(SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {SOURCE}")

    frame_id = 0
    prev_time = time.time()

    print("Starting live detection. Press Ctrl+C to stop.")

    try:
        with open(SESSION_LOG_JSONL, "a") as log_file:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Stream ended or frame grab failed.")
                    break

                results = model.track(
                    frame,
                    persist=True,
                    classes=[0],           
                    conf=CONF_THRESHOLD,
                    iou=IOU_THRESHOLD,
                    tracker=TRACKER_CONFIG,
                    imgsz=IMG_SIZE,
                    verbose=False
                )
                result = results[0]

                now = time.time()
                fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now

                frame_json = build_frame_json(frame_id, frame.shape, result, fps)

                with open(LATEST_FRAME_JSON, "w") as f:
                    json.dump(frame_json, f, indent=2)

                log_file.write(json.dumps(frame_json) + "\n")
                log_file.flush()

                print(f"Frame {frame_id:>6} | People: {frame_json['people_count']:>3} | "
                      f"FPS: {frame_json['processing_fps']:>5.1f}")

                frame_id += 1

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        cap.release()
        print(f"\nLatest frame JSON: {LATEST_FRAME_JSON}")
        print(f"Full session log:  {SESSION_LOG_JSONL}")


if __name__ == "__main__":
    run()
