from ultralytics import YOLO
from pathlib import Path
import cv2
import time
import json

# ======================================
# CHANGE ONLY THIS
# ======================================
# MODEL_NAME = "yolov8n.pt"
# MODEL_NAME = "yolo11n.pt" # conf 0.15
MODEL_NAME = "yolo26n.pt" # conf 0.15

# ======================================
# Load Model
# ======================================
model = YOLO(MODEL_NAME)

VIDEO_FOLDER = Path("../datasets/videos")

OUTPUT_FOLDER = Path(f"../outputs/{MODEL_NAME[:-3]}/videos")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

videos = sorted(VIDEO_FOLDER.glob("*.mp4"))

benchmark = {
    "model": MODEL_NAME,
    "videos_tested": 0,
    "videos": []
}

print("=" * 65)
print(f"Video Benchmark : {MODEL_NAME}")
print("=" * 65)

for video in videos:

    print(f"\nProcessing {video.name}...")

    cap = cv2.VideoCapture(str(video))

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    duration = frame_count / fps if fps else 0

    cap.release()

    start = time.perf_counter()

    model.predict(
        source=str(video),
        classes=[0],          # Person only
        save=True,
        conf=0.15,
        project=str(OUTPUT_FOLDER),
        name="",
        verbose=False
    )

    end = time.perf_counter()

    runtime = end - start
    avg_frame_time_ms = (runtime / frame_count) * 1000 if frame_count else 0

    processed_fps = frame_count / runtime if runtime else 0

    benchmark["videos"].append({
        "video": video.name,
        "frames": frame_count,
        "duration_seconds": round(duration, 2),
        "processing_time_seconds": round(runtime, 2),
        "processed_fps": round(processed_fps, 2),
        "average_frame_time_ms": round(avg_frame_time_ms, 2)
    })

    print(f"Frames      : {frame_count}")
    print(f"Duration    : {duration:.2f} s")
    print(f"Runtime     : {runtime:.2f} s")
    print(f"FPS         : {processed_fps:.2f}")

benchmark["videos_tested"] = len(videos)

benchmark_path = Path("../benchmarks")
benchmark_path.mkdir(exist_ok=True)

with open(
    benchmark_path / f"{MODEL_NAME[:-3]}_videos.json",
    "w"
) as f:
    json.dump(benchmark, f, indent=4)

print("\nBenchmark Complete!")