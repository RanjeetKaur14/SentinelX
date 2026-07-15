"""
finetune_person.py
Fine-tunes YOLOv8n - starting from its existing COCO weights, not from
scratch - on CrowdHuman, to make it more robust to dense/occluded crowds
while keeping everything it already learned about "what a person looks like".

Run this in Colab/Kaggle with a GPU runtime after prepare_crowdhuman.py
has produced crowdhuman_yolo/.

Why these settings:
- epochs=40, low lr0: this is fine-tuning, not training from scratch.
  A known failure mode reported by others training YOLOv8 on CrowdHuman from
  scratch for 300 epochs is overfitting (train metrics improve, val metrics
  stall/worsen). Starting from COCO weights with a short, low-LR fine-tune
  avoids most of that, since the model isn't relearning "person" from zero.
- single_cls=True: we only converted the "person" full-body class, so there's
  nothing else to classify.
- patience=10: stops early if val mAP stalls, which is your real defense
  against overfitting - watch the printed val mAP each epoch, not just train loss.
"""

from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # start from COCO-pretrained weights

results = model.train(
    data="crowdhuman.yaml",
    epochs=25,
    imgsz=640,
    batch=16,            # lower to 8 if you hit a CUDA/RAM out-of-memory error
    patience=10,          # early stop if val mAP doesn't improve for 10 epochs
    single_cls=True,
    lr0=0.001,             # lower than a from-scratch training LR - we're fine-tuning
    optimizer="SGD",
    cos_lr=True,
    augment=True,
    mosaic=1.0,
    fliplr=0.5,
    degrees=5,
    translate=0.1,
    scale=0.5,
    project="/content/drive/MyDrive/SentinelX/outputs",
    name="yolov8n-crowdhuman",
    pretrained=True,
    workers=8,
    device=0,             # set to "cpu" only if no GPU is available (very slow for this dataset size)
    val=True,
    plots=True,
)

# Export the best checkpoint to ONNX too, useful once you move to the Pi 5
# best_model = YOLO("runs/finetune/yolov8n-crowdhuman/weights/best.pt")
best_model = YOLO("/content/drive/MyDrive/SentinelX/outputs/yolov8n-crowdhuman/weights/best.pt")
best_model.export(format="onnx", simplify=True)

print("\nFine-tuning complete.")
# print("Best weights: runs/finetune/yolov8n-crowdhuman/weights/best.pt")
print("Best weights: /content/drive/MyDrive/SentinelX/outputs/yolov8n-crowdhuman/weights/best.pt")
# print("ONNX export:  runs/finetune/yolov8n-crowdhuman/weights/best.onnx")
print("ONNX export: /content/drive/MyDrive/SentinelX/outputs/yolov8n-crowdhuman/weights/best.onnx")
print("\nCompare best.pt against your original yolov8n.pt using your existing")
print("benchmark script before swapping it into crowd_detector.py.")
