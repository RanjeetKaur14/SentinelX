"""
CrowdShield - Live Video Server
Runs YOLOv8n person detection + tracking on a video/CCTV source and serves:
  - GET /video_feed  -> MJPEG stream with bounding boxes drawn in, for the
                         frontend <img> tag to render as a live video
  - GET /api/stats    -> lightweight JSON (people count, fps, timestamp) for
                         UI counters/badges without decoding the video stream

Run:  uvicorn live_server:app --host 0.0.0.0 --port 8000
"""

import cv2
import time
import threading
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from ultralytics import YOLO

# ============================================================
# CONFIG - edit these for your setup
# ============================================================
MODEL_PATH = "best.pt"                  # your CrowdHuman fine-tuned weights
SOURCE = "testing/datasets/videos/v2.mp4"  # same source best.py uses - swap to 0/RTSP for a real camera
CONF_THRESHOLD = 0.35
IOU_THRESHOLD = 0.5
TRACKER_CONFIG = "bytetrack.yaml"
IMG_SIZE = 640
JPEG_QUALITY = 80                       # lower = smaller/faster stream over the network, higher = sharper

BOX_COLOR = (160, 229, 0)               # BGR - matches the frontend's accent green
BOX_THICKNESS = 2

# ============================================================
# SHARED STATE
# Written by the background detection thread, read by the API routes.
# A lock guards it since FastAPI/uvicorn can serve requests concurrently.
# ============================================================
state_lock = threading.Lock()
latest_jpeg = None
latest_stats = {"people_count": 0, "fps": 0.0, "timestamp": None}


def detection_loop():
    global latest_jpeg, latest_stats

    print(f"Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(SOURCE)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {SOURCE}")

    prev_time = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            if isinstance(SOURCE, str):
                # loop a test video file instead of dying mid-demo
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            print("Stream ended.")
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

        people_count = 0
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            has_ids = boxes.id is not None
            ids = boxes.id.cpu().tolist() if has_ids else [None] * len(boxes)
            confs = boxes.conf.cpu().tolist()
            xyxy = boxes.xyxy.cpu().tolist()
            people_count = len(boxes)

            for track_id, conf, (x1, y1, x2, y2) in zip(ids, confs, xyxy):
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)

                label = f"#{int(track_id)} {conf:.2f}" if track_id is not None else f"{conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), BOX_COLOR, -1)
                cv2.putText(frame, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA)

        ok_enc, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        if not ok_enc:
            continue

        with state_lock:
            latest_jpeg = buffer.tobytes()
            latest_stats = {
                "people_count": people_count,
                "fps": round(fps, 1),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


def mjpeg_generator():
    while True:
        with state_lock:
            frame_bytes = latest_jpeg
        if frame_bytes is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.01)  # yield control instead of spinning a core while waiting on the first frame


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="CrowdShield Live Feed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your actual frontend origin before demoing on a shared/public network
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_detection_thread():
    thread = threading.Thread(target=detection_loop, daemon=True)
    thread.start()


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/stats")
def stats():
    with state_lock:
        return JSONResponse(latest_stats)
