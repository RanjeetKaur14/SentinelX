# Technical Report

SentinelX uses two fine-tuned detectors depending on crowd density (see [`ARCHITECTURE.md`](../ARCHITECTURE.md#why-two-detection-models)). Specs below are split per model. All figures for the person model are measured on the developer's laptop (CPU-only inference); the deployment target is a Raspberry Pi 4/5, and Pi-specific numbers are estimates pending on-device benchmarking.

---

## 1. Person (body) detection model

| Item | Detail |
|---|---|
| Architecture | YOLOv8n (Ultralytics)|
| Base checkpoint | `yolov8n.pt` (COCO-pretrained) |
| Fine-tuning data | [CrowdHuman](https://www.crowdhuman.org/) full-body boxes, converted to a single `person` class |
| Fine-tuning config | 25 epochs, imgsz 640, batch 16, SGD, `lr0=0.001`, cosine LR schedule, early-stop patience 10, `single_cls=True`, augmentation: mosaic 1.0, `fliplr=0.5`, `degrees=5`, `translate=0.1`, `scale=0.5` |
| Optimization applied | Domain fine-tuning (the primary optimization here): `yolov8n.pt` is COCO-pretrained on 80 general classes, so its `person` detections in real crowd footage- small, occluded, densely packed bodies, are meaningfully weaker out of the box. Fine-tuning on CrowdHuman single-class `person` data specializes the same nano-sized (6 MB) architecture for exactly this use case, buying accuracy without paying any latency/size cost over the base model (see the pre- vs. post-fine-tune comparison in [`EVALUATION.md`](EVALUATION.md#1-detector-selection-benchmark-baseline-comparison))|
| Quantization|Not yet applied. ONNX export and INT8 quantization are planned for Raspberry Pi deployment.|
| Model size | 6.0 MB measured on disk |
| Tracker (detection stage) | ByteTrack, via Ultralytics' built-in tracker (`bytetrack.yaml`) |
| Inference settings used | `conf=0.35`, `iou=0.5`, `imgsz=640`, `classes=[0]` |

### Training environment and cost (measured, Google Colab)

| Item | Value |
|---|---|
| Training software | Ultralytics 8.4.92, Python 3.12.13, PyTorch 2.11.0+cu128 |
| Training hardware | 1× Tesla T4 GPU (14,913 MiB), Google Colab |
| Training data used | 10,000 of the 15,000 available CrowdHuman training images (val: full 4,370-image split) |
| Training duration | 25 epochs in 2.771 hours |
| Model complexity | Train graph: 130 layers, 3,011,043 params, 8.2 GFLOPs. Fused (inference) graph: 73 layers, 3,005,843 params, 8.1 GFLOPs |
| GPU validation speed | 0.2 ms preprocess + 6.9 ms inference + 2.4 ms postprocess ≈ 9.5 ms/image|

### Measured latency / throughput (developer laptop, CPU, post fine-tune)

From a live tracked run (`best.py`, detection + ByteTrack, single process) over a 1303-frame test video:

| Metric | Value |
|---|---|
| Frames processed | 1,303 |
| Average processing FPS | 12.68 |
| FPS range | 0.47 – 15.9|
| Implied average frame time | ~78.9 ms/frame (detection + tracking combined) |
| Average people detected per frame | 58.6 (max observed: 88) |

Pre-fine-tune, CPU-only, model-selection benchmark (8 test images, dev machine, same hardware) for reference (see [`EVALUATION.md`](EVALUATION.md) for the full three-model comparison):

| Model | Avg. inference (ms/img) | Video throughput (FPS) |
|---|---|---|
| YOLOv8n (base, pre-fine-tune) | 110.7 | 11.2 – 14.6 |

### End-to-end pipeline (detection → analytics → risk scoring)

From a full integration run (`integration/pipeline.py`) over 2,627 frames:

| Metric | Value |
|---|---|
| Frames processed | 2,627 |
| Average people count | 45.7 (max observed: 81) |
| Average risk score | 9.4 / 100 |
| Max risk score observed | 45 (Yellow) |
| Risk level distribution | Green: 2,289 frames, Yellow: 338 frames |
| Average FPS | ~11.7 |


### CPU usage, peak memory, tested device specs

| Item | Value |
|---|---|
| Tested device | Developer laptop, CPU-only inference |
| Raspberry Pi 4/5 (target) | Not yet benchmarked on-device. Estimated application footprint ~260–480 MB (see below)|

### Estimated storage/resource footprint on Raspberry Pi (not yet measured on-device)

| Component | Size |
|---|---|
| Fine-tuned detection weights (`best.pt`) | 6.0 MB (measured) |
| ONNX export of `best.pt` | ~6–8 MB |
| Ultralytics + ONNX Runtime (ARM) | ~40–90 MB |
| OpenCV (`opencv-python-headless`) | ~40–90 MB |
| Python 3.11 + virtual environment | ~150–250 MB |
| FastAPI + Uvicorn + dependencies | ~20–30 MB |
| React production build (static assets) | ~5–15 MB |
| **Estimated total application footprint** | **~260–480 MB** |
| Recommended SD card | 16 GB minimum, 32 GB recommended |

---

## 2. Head detection model


| Item | Detail |
|---|---|
| Architecture | YOLOv8n (Ultralytics) |
| Base checkpoint | `yolov8n.pt` (COCO-pretrained) |
| Fine-tuning data | [CrowdHuman](https://www.crowdhuman.org/) `hbox` (head box) annotations only, converted to a single `head` class via `convert_crowdhuman_to_yolo.py`.  |
| Fine-tuning config | Configured for up to 20 epochs, imgsz 960, batch 16, `device=0` (GPU), augmentation: mosaic 1.0, `copy_paste=0.3` |
| Optimizer actually used | `optimizer=auto` in the script resolved to AdamW, `lr0=0.002`, `momentum=0.9`, weight decay 0.0005 across 3 parameter groups|
| Optimization applied | Domain fine-tuning, same rationale as the person model: `yolov8n.pt` is fine-tuned on CrowdHuman `hbox` data rather than used as a general COCO detector, specializing the same lightweight architecture for small, densely-packed heads instead of full bodies. Layered on top of that, two hyperparameters were specifically raised for this harder small-object case: `imgsz` 640→960 (more pixels per head at a distance) and `copy_paste=0.3` (synthetically increases training-image crowd density), both zero-cost at inference time since they only affect training, not the deployed model's size or speed |
| Quantization|Not yet applied. ONNX export and INT8 quantization are planned for Raspberry Pi deployment.|
| Tracker used | ByteTrack with a custom config, tuned for dense, occlusion-heavy crowds: track_buffer 30→90 frames, new_track_thresh 0.25→0.45, match_thresh 0.8→0.75|

### Training environment and cost 

| Item | Value |
|---|---|
| Training software | Ultralytics 8.4.95, Python 3.12.13, PyTorch 2.11.0+cu128 |
| Training hardware | 1× Tesla T4 GPU (14,913 MiB), Google Colab |
| Training data used | 5,000 training images (99,394 head instances) / 4,370 validation images, from `convert_crowdhuman_to_yolo.py` output.|
| Model complexity | 130 layers, 3,011,043 params, 3,011,027 gradients, 8.2 GFLOPs |
| Training duration | 20 epochs in ~2.4 hours (train + validation time per epoch, Tesla T4) |
| Final metrics (epoch 20, full 4,370-image val split, imgsz 960) | Precision **0.841**, Recall **0.635**, mAP50 **0.719**, mAP50-95 **0.431** |


---

## 3. Other components (non-AI runtime footprint)

| Component | Runtime |
|---|---|
| Crowd Analytics Engine | Python 3.11, NumPy only |
| Risk Engine | Python 3.11, FastAPI 0.139.0 / Uvicorn 0.51.0 / Pydantic 2.13.4 |
| Dashboard | React 18.3.1 + Vite 5.4.8 + Tailwind 3.4.13 + Chart.js 4.4.4 |