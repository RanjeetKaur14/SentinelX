from ultralytics import YOLO
from pathlib import Path
import json

# MODEL_NAME = "yolov8n.pt"
# MODEL_NAME = "yolo11n.pt"
MODEL_NAME = "yolo26n.pt"

model = YOLO(MODEL_NAME)

IMAGE_FOLDER = Path("../datasets/images")

OUTPUT_FOLDER = Path(f"../outputs/{MODEL_NAME[:-3]}")
IMAGE_OUTPUT = OUTPUT_FOLDER / "images"

IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)

benchmark = {
    "model": MODEL_NAME,
    "images_tested": 0,
    "summary": {
        "total_persons": 0,
        "average_confidence": 0,
        "average_inference_time_ms": 0
    },
    "images": []
}

# ==========================================
# Read Images
# ==========================================
images = sorted(IMAGE_FOLDER.glob("*.jpg"))

print("=" * 65)
print(f"Benchmarking {MODEL_NAME}")
print("=" * 65)

print(f"\nFound {len(images)} images")

print("\nWarming up model...")
model(images[0], verbose=False)
print("Warm-up complete!\n")

print("-" * 65)
print(f"{'Image':10} {'Persons':8} {'Avg Conf':10} {'Infer(ms)':10}")
print("-" * 65)

total_people = 0
total_confidence = 0
total_inference = 0

for image in images:

    results = model(
        image,
        verbose=False,
        save=True,
        classes=[0], 
        project=IMAGE_OUTPUT,
        name=""
    )

    result = results[0]

    person_boxes = result.boxes[result.boxes.cls == 0]

    person_count = len(person_boxes)

    if person_count:
        avg_conf = person_boxes.conf.mean().item()
    else:
        avg_conf = 0

    inference_time = result.speed["inference"]

    benchmark["images"].append({
        "image": image.name,
        "persons_detected": person_count,
        "average_confidence": round(avg_conf, 3),
        "inference_time_ms": round(inference_time, 2)
    })

    total_people += person_count
    total_confidence += avg_conf
    total_inference += inference_time

    print(
        f"{image.name:10}"
        f"{person_count:^10}"
        f"{avg_conf:^12.2f}"
        f"{inference_time:^12.2f}"
    )

benchmark["images_tested"] = len(images)

benchmark["summary"]["total_persons"] = total_people

benchmark["summary"]["average_confidence"] = round(
    total_confidence / len(images),
    3
)

benchmark["summary"]["average_inference_time_ms"] = round(
    total_inference / len(images),
    2
)

benchmark_path = Path("../benchmarks")
benchmark_path.mkdir(exist_ok=True)

with open(
    benchmark_path / f"{MODEL_NAME[:-3]}.json",
    "w"
) as f:
    json.dump(benchmark, f, indent=4)

print("\n" + "=" * 65)
print("SUMMARY")
print("=" * 65)
print(f"Images Tested            : {benchmark['images_tested']}")
print(f"Total Persons Detected   : {total_people}")
print(f"Average Confidence       : {benchmark['summary']['average_confidence']}")
print(f"Average Inference Time   : {benchmark['summary']['average_inference_time_ms']} ms")
print(f"\nJSON Saved To: {benchmark_path / f'{MODEL_NAME[:-3]}.json'}")
print(f"Annotated Images Saved To: {IMAGE_OUTPUT}")