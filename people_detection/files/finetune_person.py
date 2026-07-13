from ultralytics import YOLO

model = YOLO("yolov8n.pt") 

results = model.train(
    data="crowdhuman.yaml",
    epochs=25,
    imgsz=640,
    batch=16,           
    patience=10,      
    single_cls=True,
    lr0=0.001,            
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
    device=0,             
    val=True,
    plots=True,
)
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
