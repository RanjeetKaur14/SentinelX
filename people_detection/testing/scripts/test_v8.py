from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model("../datasets/images/c1.jpg",save=True)
print("Model loaded successfully")