"""
pipeline.py
-----------
SentinelX end-to-end orchestrator: People Detection -> Crowd Analytics
-> Risk Engine, running in a single process (no HTTP hop needed for a
demo/hackathon setting -- everything below is a direct Python call).

DIRECTORY LAYOUT THIS SCRIPT ASSUMES
=====================================
project_root/
  people_detection/
    best.pt
    best.py
  crowd_analysis/
    analytics/            <- a package (has __init__.py)
      __init__.py, config.py, analytics_engine.py, models.py, ...
  risk_engine/
    models.py, risk_engine.py, alert_engine.py, database.py   <- FLAT modules,
      not a package (they import each other as `from models import ...`,
      so risk_engine/ itself must be on sys.path, not its parent).
  integration/
    adapter.py             <- detector-JSON -> analytics-input converter
    risk_engine_fixed.py    <- corrected calculate_risk() (see file header
                               for why the original is broken)
    pipeline.py             <- this file

Adjust PROJECT_ROOT below (or pass paths via CLI args) to match where
you actually put things.
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

import cv2
from ultralytics import YOLO

# ------------------------------------------------------------------
# 1. WIRE UP IMPORT PATHS
# ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent          # adjust if you lay files out differently

CROWD_ANALYSIS_DIR = PROJECT_ROOT / "crowd_analysis"   # contains the `analytics` package
RISK_ENGINE_DIR = PROJECT_ROOT / "risk_engine"         # flat modules

sys.path.insert(0, str(CROWD_ANALYSIS_DIR))   # so `from analytics.analytics_engine import ...` works
sys.path.insert(0, str(RISK_ENGINE_DIR))      # so risk_engine's flat `from models import Analytics` works
sys.path.insert(0, str(HERE))                 # so `from adapter import ...` works

from analytics.analytics_engine import AnalyticsEngine          # crowd_analysis
from analytics.config import EngineConfig
from models import Analytics                                    # risk_engine's pydantic model
from risk_engine_fixed import calculate_risk                    # OUR fixed version
from alert_engine import generate_alerts                        # risk_engine's alert generator
from adapter import detector_frame_to_analytics_input, frame_timestamp


# ------------------------------------------------------------------
# 2. DETECTION -> FRAME JSON (same logic as best.py's build_frame_json)
# ------------------------------------------------------------------
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
                "bbox": {
                    "x1": round(x1, 1), "y1": round(y1, 1),
                    "x2": round(x2, 1), "y2": round(y2, 1),
                },
            })
    return {
        "frame_id": frame_id,
        # Source-aware timestamp (float seconds) -- see
        # adapter.frame_timestamp() docstring. This used to always be
        # datetime.now(), which silently corrupted average_speed /
        # stationary_tracks for recorded-file sources whenever the
        # loop ran slower than the video's native frame rate.
        "timestamp": timestamp,
        "frame_width": width,
        "frame_height": height,
        "processing_fps": round(fps, 2),
        "people_count": len(detections),
        "detections": detections,
    }


# ------------------------------------------------------------------
# 3. MAIN LOOP: detect -> adapt -> analyze -> assess risk -> log
# ------------------------------------------------------------------
def run(source, model_path, camera_id, conf_thres=0.35, iou_thres=0.5,
        imgsz=640, output_dir="./sentinelx_output", save_video=True):

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "risk_log.jsonl"
    video_path = output_dir / "annotated.mp4"

    model = YOLO(model_path)
    engine = AnalyticsEngine(EngineConfig())

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open source: {source}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30

    writer = None
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(video_path), fourcc, fps_video, (width, height))

    frame_id = 0
    prev_time = time.time()

    print(f"Writing risk log to:      {log_path}")
    if save_video:
        print(f"Writing annotated video to: {video_path}")

    with open(log_path, "a") as log_file:
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    print("Stream ended or frame grab failed.")
                    break

                # ---- Stage 1: detection + tracking (YOLO/ByteTrack) ----
                results = model.track(
                    frame, persist=True, classes=[0],
                    conf=conf_thres, iou=iou_thres,
                    tracker="bytetrack.yaml", imgsz=imgsz, verbose=False,
                )
                result = results[0]

                if writer is not None:
                    writer.write(result.plot(line_width=1, font_size=6, conf=False))

                now = time.time()
                fps = 1.0 / max(now - prev_time, 1e-6)
                prev_time = now

                ts = frame_timestamp(cap, 0 if str(source) == "0" else source, frame_id)
                detector_frame = build_detector_frame(frame_id, frame.shape, result, fps, ts)

                # ---- Adapter: detector JSON -> analytics input ----
                analytics_input = detector_frame_to_analytics_input(
                    detector_frame, camera_id=camera_id
                )

                # ---- Stage 2: crowd analytics ----
                analytics_result = engine.process_frame(analytics_input)

                # ---- Stage 3: risk scoring ----
                analytics_obj = Analytics(**analytics_result)
                score, level, reasons = calculate_risk(analytics_obj)
                alerts = generate_alerts(level, reasons)

                record = {
                    "frame": frame_id,
                    "people_count": analytics_result["crowd_metrics"]["people_count"],
                    "risk_score": score,
                    "risk_level": level,
                    "reasons": reasons,
                    "alerts": alerts,
                }
                log_file.write(json.dumps(record) + "\n")
                log_file.flush()

                print(f"Frame {frame_id:>6} | People: {record['people_count']:>3} | "
                      f"Risk: {level:>6} ({score:>3}) | {reasons}")

                frame_id += 1

        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            cap.release()
            if writer is not None:
                writer.release()
            print(f"\nLog written to:   {log_path}")
            if save_video:
                print(f"Video written to: {video_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelX end-to-end pipeline")
    parser.add_argument("--source", default="testing/datasets/videos/v2.mp4",
                         help="0 for webcam, RTSP URL, or video file path")
    parser.add_argument("--model", default="best.pt")
    parser.add_argument("--camera-id", default="cam_01")
    parser.add_argument("--output-dir", default="./sentinelx_output",
                         help="Where risk_log.jsonl and annotated.mp4 get written")
    parser.add_argument("--no-video", action="store_true",
                         help="Skip writing the annotated video (faster, log-only)")
    args = parser.parse_args()
    run(args.source, args.model, args.camera_id,
        output_dir=args.output_dir, save_video=not args.no_video)
