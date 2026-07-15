# Evaluation

## 1. Detector selection benchmark (baseline comparison)

Before committing to a base architecture, three nano-scale YOLO detectors were benchmarked head-to-head, **pre-fine-tuning**, on the same 8 test images and 2 test videos (dev-machine CPU):

| Model | Persons detected (8 imgs) | Avg. confidence | Avg. inference (ms/img) | Video throughput (FPS) |
|---|---|---|---|---|
| YOLOv8n | 80 | 0.427 | 110.7 | 11.2 – 14.6 |
| YOLO11n | 63 | 0.462 | 100.9 | 10.3 – 14.5 |
| YOLO26n | 88 | 0.326 | 102.1 | 10.9 – 14.0 |

**Method:** each model run at the same confidence/IOU settings over the same 8 static images and 2 recorded videos; persons counted, per-detection confidence averaged, and per-image/per-frame inference time recorded directly from the Ultralytics inference call. Raw artifacts: `people_detection/testing/benchmarks/*.json`.

**Interpretation:** YOLOv8n was selected as the fine-tuning base: it detects substantially more persons than YOLO11n while holding a materially higher average confidence than YOLO26n, which gives the best usable precision/recall balance for a risk engine that reasons over confidence-weighted counts. 

## 2. Post-fine-tune validation (person model)

| Run | Frames | Avg. people/frame | Max people/frame | Avg. FPS |
|---|---|---|---|---|
| Detection + tracking only (`best.py`, `v2.mp4`) | 1,303 | 58.6 | 88 | 12.68 (measured) |

## 3. Formal accuracy: CrowdHuman validation split (training-time)

(Training environment, hardware, duration, and model size/compute for this same run are documented once, in [`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md#training-environment-and-cost-measured-google-colab))

| Metric | Value |
|---|---|
| Validation set | CrowdHuman val split, 4,370 images, 99,481 person instances |
| Precision (Box P) | 0.797 |
| Recall (Box R) | 0.644 |
| mAP50 | 0.759 |
| mAP50-95 | 0.457 |
| Per-image speed (GPU, batch validation) | ≈9.5 ms/image (Tesla T4) |


## 5. Head model evaluation

(Training environment, hardware, duration, and model complexity for this same run are documented once, in [`TECHNICAL_REPORT.md`](TECHNICAL_REPORT.md#training-environment-and-cost-head-model--final-20-epochs))
 
| Metric | Value |
|---|---|
| Validation set | CrowdHuman val split, 4,370 images, 99,394 head instances |
| Precision (Box P) | 0.841 |
| Recall (Box R) | 0.635 |
| mAP50 | 0.719 |
| mAP50-95 | 0.431 |
| Epoch | 20 |
 
## 6. Known failure cases / limitations

- **Severe occlusion in extremely dense crowds** reduces detection accuracy- this is the primary motivation for the separate head model.

- **Camera placement and viewing angle** matter: detection reliability drops for extreme angles, very low or oblique cameras, or partial frame coverage of the monitored area.
- **Lighting/weather sensitivity**: poor lighting, rain, fog, or strong backlighting reduce detection reliability; no low-light-specific augmentation or testing has been done yet.
- **Risk thresholds are unvalidated on real incident data**: all scoring thresholds (e.g. `people_count > 150`, concentration `> 0.65`) are reasonable starting points carried over from the original design, not calibrated against labeled high-risk footage, they're expected to need per-venue tuning.
- **Single-class detection** (`single_cls=True`) means the person model cannot distinguish person subtypes (e.g. staff vs. attendee, adult vs. child).
