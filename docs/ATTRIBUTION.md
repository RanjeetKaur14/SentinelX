# Attribution

## Pretrained models

| Model | Source | Used for | License note |
|---|---|---|---|
| `yolov8n.pt` (COCO-pretrained) | [Ultralytics](https://github.com/ultralytics/ultralytics) | Base checkpoint, fine-tuned into the person (body) detector | Ultralytics YOLO is released under **AGPL-3.0**; commercial use outside AGPL terms requires an Ultralytics Enterprise license. Confirm license terms suit your deployment before commercial use. |
| YOLO11n, YOLO26n | [Ultralytics](https://github.com/ultralytics/ultralytics) | Benchmarked as alternative bases during model selection (not used in the final system) | Same as above |

## Datasets

| Dataset | Source | Used for | License note |
|---|---|---|---|
| CrowdHuman | [crowdhuman.org](https://www.crowdhuman.org/) | Fine-tuning data for both the person (full-body box) and head (`hbox`) detectors | CrowdHuman's terms of use restrict the data to **non-commercial research and educational purposes**, and prohibit redistributing the images. This project's use (fine-tuning for a hackathon submission) falls under that scope, any future commercial deployment would need to revisit training-data licensing (e.g. re-training on a commercially-licensed or in-house dataset). |

## Libraries and frameworks

| Library | Used for |
|---|---|
| [Ultralytics](https://github.com/ultralytics/ultralytics) (YOLO, ByteTrack integration) | Detection, fine-tuning, ONNX export, tracking |
| OpenCV (`opencv-python`) | Video/frame capture and annotation |
| NumPy | Crowd analytics engine (density, flow, tracker) |
| pytest | Crowd analytics test suite |
| FastAPI, Uvicorn, Pydantic, Starlette, anyio, h11 | Risk engine REST API |
| React, React DOM, Vite, Tailwind CSS, PostCSS, Autoprefixer, Chart.js | Dashboard |
| Hugging Face Hub, Pillow, tqdm | Fine-tuning tooling (dataset prep / weights handling) |

## APIs

None. SentinelX makes no calls to any external API at inference time (see [`LOCAL_AI_VERIFICATION.md`](LOCAL_AI_VERIFICATION.md)).

## Pre-existing work

- ByteTrack tracking algorithm, used via its Ultralytics integration (`bytetrack.yaml`), not re-implemented.
- The crowd-analytics engine's centroid tracker, density/flow/heatmap logic, and the risk-scoring rules are original work for this project, not adapted from an existing published system.
