"""
stream_server.py
------------------
The live backbone for the dashboard: runs detection -> analytics ->
risk scoring continuously, and exposes two things over HTTP for the
React dashboard to consume directly:

    GET /video_feed    -> MJPEG live stream of annotated frames
    GET /live_status    -> JSON: people_count, fps, risk_score,
                           risk_level, reasons, alerts, per-zone density

ARCHITECTURE CHOICE, AND WHY
------------------------------
This does NOT reimplement risk scoring -- it POSTs each frame's
Analytics payload to your existing risk_engine FastAPI service's
POST /risk/check, and uses whatever that returns. Keeps risk_engine as
the single source of truth for scoring/history/alerts.

WHY TWO THREADS, AND WHY THE VIDEO IS CHOPPY BY DESIGN
---------------------------------------------------------
Earlier version of this file drew the LAST KNOWN detection boxes onto
the NEWEST raw frame every ~33ms, to make the video look smooth. That
backfired: boxes only get recomputed every ~1-2.5s, so by the time
they're drawn on a "current" frame, the crowd has actually moved --
people entered/left frame, shifted position -- and the result looks
like the model is missing people or drawing boxes in the wrong place,
even though the boxes were correct for the (older) frame they were
computed on. Decided: correctness over smoothness -- the video only
updates when a NEW detection actually completes, and it always shows
the EXACT frame those boxes were computed from. This makes the video
choppy again (same visible update rate as the original single-loop
version), but every frame you see on screen is guaranteed accurate.

capture_loop     - owns `cap` exclusively. Just reads raw frames as
                   fast as the source provides them (paced to native
                   fps for a recorded file) and publishes the latest
                   raw frame + its real video frame index. Does NOT
                   draw or encode anything.

detection_loop   - pulls the latest raw frame, runs YOLO tracking on
                   it, draws boxes on THAT SAME frame immediately, and
                   publishes the encoded JPEG right there -- frame and
                   boxes are never separated. Also does the throttled
                   analytics + risk_engine call.

If you want smoothness back at the cost of staleness, that's the
earlier two-thread-with-img-override design -- ask for it explicitly,
don't reintroduce it by accident while "improving" this file.

Run risk_engine separately first:
    cd risk_engine && uvicorn app:app --port 8000
Then run this:
    cd integration && uvicorn stream_server:app --port 8001 --reload
"""

import os
import sys
import time
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timezone

import cv2
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from ultralytics import YOLO

# ------------------------------------------------------------------
# import paths (same layout as pipeline.py)
# ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
CROWD_ANALYSIS_DIR = PROJECT_ROOT / "crowd_analysis"

sys.path.insert(0, str(CROWD_ANALYSIS_DIR))
sys.path.insert(0, str(HERE))

from analytics.analytics_engine import AnalyticsEngine
from analytics.config import EngineConfig
from adapter import detector_frame_to_analytics_input, frame_timestamp

# ------------------------------------------------------------------
# CONFIG -- set via environment variables, e.g.:
#   SOURCE=../people_detection/testing/datasets/videos/v1.mp4 \
#   MODEL_PATH=../people_detection/head_best.pt \
#   uvicorn stream_server:app --port 8001
# ------------------------------------------------------------------
MODEL_PATH = os.environ.get("MODEL_PATH", str(PROJECT_ROOT / "people_detection" / "best.pt"))
# NOTE: "head_best.pt" (the old default here) never existed anywhere in
# this project -- every other script (pipeline.py, live_server.py,
# best.py) loads people_detection/best.pt, the actual CrowdHuman
# fine-tuned weights. With the old default, YOLO() had nothing valid to
# load unless MODEL_PATH was set manually, which silently killed
# detection_loop -- that's why boxes stopped appearing even though the
# conf/imgsz tuning below is correct. Fixed to point at the real file.
SOURCE = os.environ.get("SOURCE", "0")               # "0" for webcam, or a video file path / RTSP URL
CAMERA_ID = os.environ.get("CAMERA_ID", "cam_01")
TRACKER_CONFIG = os.environ.get("TRACKER_CONFIG", "bytetrack_custom.yaml")
CONF_THRESHOLD = float(os.environ.get("CONF_THRESHOLD", "0.25"))
# Lowered default from 0.35 -> 0.25: with speed deprioritized, trading
# some false-positive risk for catching more low-confidence heads
# (small/distant/partially-occluded) is the right call. Raise back
# toward 0.35+ if you start seeing boxes on things that clearly aren't
# heads.
IOU_THRESHOLD = 0.5
# Back to 960 (was dropped to 640 to fight video staleness, which
# directly costs recall on small/distant heads -- the wrong trade now
# that accuracy matters more than smoothness). Go to 1280 if this
# still isn't catching enough of a very dense/high-res crowd, at
# further speed cost.
IMG_SIZE = int(os.environ.get("IMG_SIZE", "960"))
RISK_ENGINE_URL = os.environ.get("RISK_ENGINE_URL", "http://localhost:8000")
RISK_CHECK_INTERVAL_SEC = 1.0

engine_config = EngineConfig()
GRID_ROWS = engine_config.density.grid_rows
GRID_COLS = engine_config.density.grid_cols

# ------------------------------------------------------------------
# SHARED STATE
# ------------------------------------------------------------------
# Two separate locks on purpose: frame_lock guards the fast-changing
# raw frame + latest detection result (touched every ~30fps by
# capture_loop), status_lock guards the slower-changing status dict
# (touched ~1x/sec by detection_loop, including a network call to
# risk_engine). Using one lock for both would make capture_loop stall
# waiting behind detection_loop's risk_engine HTTP request -- exactly
# the kind of stutter we're trying to eliminate.
frame_lock = threading.Lock()
latest_raw_frame = None      # newest frame straight from the camera/file
latest_frame_index = 0       # REAL video frame count, incremented by capture_loop only.
                              # detection_loop must use THIS (not its own loop
                              # counter) for timestamps -- see frame_timestamp
                              # bug note in detection_loop below.
latest_result = None         # newest YOLO tracking Result (may be a bit stale)
latest_jpeg = None           # newest ENCODED+ANNOTATED frame for /video_feed

status_lock = threading.Lock()
latest_status = {
    "people_count": 0,
    "fps": 0.0,
    "average_speed": 0.0,
    "flow_label": "—",
    "risk_score": 0,
    "risk_level": "Green",
    "reasons": [],
    "alerts": [],
    "zones": [],          # NEW: real per-zone density for the heatmap
    "grid_rows": GRID_ROWS,   # static -- lets the frontend size the
    "grid_cols": GRID_COLS,   # overlay grid without guessing from zones.length
    "updated_at": None,
}

# Set once at startup by capture_loop, read (never written) elsewhere --
# safe without a lock.
video_native_fps = 30.0
is_live_source = SOURCE == "0"


def build_detector_frame(frame_id, frame_shape, result, fps, timestamp):
    height, width = frame_shape[:2]
    detections = []
    boxes = result.boxes
    if boxes is not None and len(boxes) > 0:
        confs = boxes.conf.cpu().tolist()
        xyxy = boxes.xyxy.cpu().tolist()
        for conf, (x1, y1, x2, y2) in zip(confs, xyxy):
            detections.append({
                "confidence": round(float(conf), 3),
                "bbox": {"x1": round(x1, 1), "y1": round(y1, 1),
                          "x2": round(x2, 1), "y2": round(y2, 1)},
            })
    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "frame_width": width,
        "frame_height": height,
        "processing_fps": round(fps, 2),
        "people_count": len(detections),
        "detections": detections,
    }


def zones_from_density(density: dict, people_count: int) -> list:
    """
    Turns crowd_metrics.density (keys "zone_1".."zone_N", raw counts)
    into the shape DensityHeatmap.jsx expects: [{id, name, density,
    count, capacity, risk}, ...].

    HONEST SIMPLIFICATION: there's no real physical "capacity" per
    grid cell anywhere in this system -- these are anonymous grid
    cells, not named/measured physical zones. Rather than fabricate a
    fake capacity number, `capacity` is set to the total people_count
    across ALL zones, so the displayed "count / capacity" reads as
    "this zone's share of the total crowd", which is honest about what
    we actually know. `density` (the bar %) is each zone's count
    relative to the SINGLE BUSIEST zone this frame -- i.e. the same
    "concentration" signal risk_engine_fixed.py's density rule uses,
    so the heatmap visually agrees with whatever triggered a density
    alert. `risk` per zone reuses those same concentration thresholds.
    """
    if not density:
        return []

    max_count = max(density.values()) if density.values() else 0
    zones = []
    for key, count in sorted(density.items(), key=lambda kv: kv[1], reverse=True):
        idx = int(key.split("_")[1]) - 1
        row, col = divmod(idx, GRID_COLS)
        concentration = (count / max_count) if max_count > 0 else 0.0

        if concentration > 0.8:
            risk = "red"
        elif concentration > 0.6:
            risk = "orange"
        elif concentration > 0.35:
            risk = "yellow"
        else:
            risk = "green"

        zones.append({
            "id": key,
            "name": f"Zone R{row + 1}C{col + 1}",
            "row": row,
            "col": col,
            "density": round(concentration, 3),
            "count": count,
            "capacity": people_count,
            "risk": risk,
        })
    return zones


def capture_loop():
    """Owns cv2.VideoCapture. Only reads frames and publishes the
    latest raw one + its real video frame index. Does NOT draw or
    encode anything -- detection_loop does that, on the exact frame
    it used for inference, to guarantee frame/box correctness."""
    global latest_raw_frame, latest_frame_index, video_native_fps

    source = 0 if SOURCE == "0" else SOURCE
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: could not open source {SOURCE}")
        return

    fps_reported = cap.get(cv2.CAP_PROP_FPS)
    video_native_fps = fps_reported if fps_reported and fps_reported > 1 else 30.0
    frame_interval = 1.0 / video_native_fps
    frame_index = 0

    while True:
        loop_start = time.time()
        ok, frame = cap.read()
        if not ok:
            print("Stream ended or frame grab failed -- restarting source in 2s.")
            time.sleep(2)
            cap.release()
            cap = cv2.VideoCapture(source)
            frame_index = 0
            continue

        frame_index += 1

        with frame_lock:
            latest_raw_frame = frame
            latest_frame_index = frame_index

        # Pace to the source's native fps for recorded files, so
        # capture doesn't race through the file far faster than
        # detection_loop could ever keep up with. Live sources
        # (webcam/RTSP) already pace themselves via cap.read() blocking.
        if not is_live_source:
            elapsed = time.time() - loop_start
            sleep_for = frame_interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)


def draw_zone_grid(frame, rows: int, cols: int):
    """
    Draws the actual grid lines + zone labels ("R1C1", etc.) onto the
    frame. Without this there was NO visual way to know where "Zone
    R1C1" in the heatmap panel actually corresponds to on screen --
    the grid only existed as invisible pixel math. This makes it real.
    """
    h, w = frame.shape[:2]
    cell_w = w / cols
    cell_h = h / rows
    color = (0, 200, 255)   # BGR -- amber, readable against most footage
    thickness = 1

    for c in range(1, cols):
        x = int(c * cell_w)
        cv2.line(frame, (x, 0), (x, h), color, thickness, cv2.LINE_AA)
    for r in range(1, rows):
        y = int(r * cell_h)
        cv2.line(frame, (0, y), (w, y), color, thickness, cv2.LINE_AA)

    for r in range(rows):
        for c in range(cols):
            label = f"R{r + 1}C{c + 1}"
            x = int(c * cell_w) + 4
            y = int(r * cell_h) + 14
            cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.35, color, 1, cv2.LINE_AA)
    return frame


def detection_loop():
    """Pulls the latest raw frame, runs YOLO tracking on it, draws
    boxes on THAT SAME frame and publishes the JPEG immediately (frame
    and boxes are never separated), and (throttled) pushes analytics +
    risk to the dashboard's status."""
    global latest_result, latest_jpeg, latest_status

    model = YOLO(MODEL_PATH)
    engine = AnalyticsEngine(engine_config)

    prev_time = time.time()
    last_risk_check = 0.0

    while True:
        with frame_lock:
            frame = latest_raw_frame.copy() if latest_raw_frame is not None else None
            frame_index_at_capture = latest_frame_index

        if frame is None:
            time.sleep(0.05)
            continue

        results = model.track(
            frame, persist=True, classes=[0],
            conf=CONF_THRESHOLD, iou=IOU_THRESHOLD,
            tracker=TRACKER_CONFIG, imgsz=IMG_SIZE, verbose=False,
        )
        result = results[0]

        # Draw + encode on THIS exact frame, right now -- guarantees
        # what /video_feed serves next is always a correct (frame,
        # boxes) pair, never boxes composited onto a newer frame.
        annotated = result.plot(line_width=1, font_size=6, conf=False)
        annotated = draw_zone_grid(annotated, GRID_ROWS, GRID_COLS)
        ok_enc, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])

        with frame_lock:
            latest_result = result
            if ok_enc:
                latest_jpeg = jpeg.tobytes()

        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now

        if now - last_risk_check >= RISK_CHECK_INTERVAL_SEC:
            last_risk_check = now
            ts = frame_index_at_capture / video_native_fps if not is_live_source else datetime.now(timezone.utc).timestamp()
            detector_frame = build_detector_frame(frame_index_at_capture, frame.shape, result, fps, ts)
            analytics_input = detector_frame_to_analytics_input(detector_frame, camera_id=CAMERA_ID)
            analytics_result = engine.process_frame(analytics_input)
            cm = analytics_result["crowd_metrics"]

            try:
                resp = requests.post(f"{RISK_ENGINE_URL}/risk/check", json=analytics_result, timeout=2)
                resp.raise_for_status()
                risk_data = resp.json()
            except Exception as e:
                print(f"WARNING: risk_engine call failed ({e}); using last known risk state.")
                risk_data = None

            zones = zones_from_density(cm["density"], cm["people_count"])

            with status_lock:
                latest_status["people_count"] = cm["people_count"]
                latest_status["fps"] = round(fps, 1)
                latest_status["average_speed"] = round(cm["average_speed"], 2)
                latest_status["flow_label"] = cm["flow"]["label"]
                latest_status["zones"] = zones
                latest_status["updated_at"] = datetime.now(timezone.utc).isoformat()
                if risk_data:
                    latest_status["risk_score"] = risk_data["risk_score"]
                    latest_status["risk_level"] = risk_data["risk_level"]
                    latest_status["reasons"] = risk_data["reasons"]
                    latest_status["alerts"] = risk_data["alerts"]


# ------------------------------------------------------------------
# FASTAPI APP
# ------------------------------------------------------------------
app = FastAPI(title="SentinelX - Live Stream Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def start_background_threads():
    threading.Thread(target=capture_loop, daemon=True).start()
    threading.Thread(target=detection_loop, daemon=True).start()


async def mjpeg_generator(request: Request):
    while True:
        # WITHOUT this check, every browser refresh / HMR reload opens a
        # new /video_feed connection while the OLD generator keeps
        # running forever in the background (it never learns the socket
        # is dead). Over a dev session that's a slow socket leak that
        # eventually exhausts Windows' non-paged socket buffer pool ->
        # WinError 10055 (WSAENOBUFS), which kills the whole server.
        if await request.is_disconnected():
            break
        with frame_lock:
            frame = latest_jpeg
        if frame is not None:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        await asyncio.sleep(0.03)   # ~30fps cap on stream output, independent of detection speed


@app.get("/video_feed")
def video_feed(request: Request):
    return StreamingResponse(mjpeg_generator(request), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/live_status")
def live_status():
    with status_lock:
        return JSONResponse(dict(latest_status))


@app.get("/")
def root():
    return {"message": "SentinelX live stream server running", "video_feed": "/video_feed", "live_status": "/live_status"}
