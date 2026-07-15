<div align="center">

## SentinelX

<a href="#"><img src="https://img.shields.io/badge/status-mid--evaluation-f59e0b?style=flat-square" /></a>
<a href="#"><img src="https://img.shields.io/badge/license-MIT-64748b?style=flat-square" /></a>
<a href="#"><img src="https://img.shields.io/badge/target-Raspberry%20Pi-1e293b?style=flat-square" /></a>

**Prevent. Protect. Predict.**
</div>

---

## Table of Contents
**In this file:**
- [What it is](#what-it-is)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Detection models](#detection-models)
- [Tech Stack](#tech-stack)
- [Pipeline](#pipeline-one-line)
- [Screenshots](#screenshots)
- [Demo Video](#demo-video)
- [Getting started](#getting-started)
- [Team](#team)
- [Limitations](#limitations)
- [Future scope](#future-scope)
- [License](#license)


**Other files:**
| Doc | Owns |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System diagram, data flow, design-decision rationale |
| [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md) | Model specs, training environment, latency, memory, footprint |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Accuracy, benchmarks, scenario tests, known failure cases |
| [`docs/LOCAL_AI_VERIFICATION.md`](docs/LOCAL_AI_VERIFICATION.md) | On-device vs. internet-dependent, what data ever leaves the device |
| [`docs/PRIVACY_AND_SAFETY.md`](docs/PRIVACY_AND_SAFETY.md) | Storage/retention, permissions, privacy risks |
| [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md) | Pretrained models, datasets, libraries, licenses |

---

## What it is

SentinelX turns an existing CCTV/webcam feed into an offline crowd-safety layer. It detects and tracks people, computes crowd analytics (density, flow, entry/exit, stationary buildup), and turns those signals into an explainable risk score, all on local edge hardware (Raspberry Pi target), with no frames ever leaving the device.

## Problem Statement

Large public gatherings: railway and metro stations, temples, stadiums, concerts, malls, festivals, college fests, routinely become overcrowded. Traditional CCTV is reactive: it records what happened, it does not stop it from happening.

A single control-room operator cannot reliably watch dozens of live feeds and catch the early signs of risk: rising density, a crowd pressing against a blocked exit, opposing movement in a corridor, before they escalate into an emergency.

## Solution

SentinelX ingests existing CCTV/webcam feeds and runs the full crowd-intelligence pipeline **on local edge hardware**:

- Detects and counts people per frame with a person detector fine-tuned for dense, occluded crowds
- Tracks individuals across frames to understand motion, not just headcount
- Estimates crowd density, builds live heatmaps, and classifies movement flow (uniform vs. mixed/opposing)
- Detects congestion, entry/exit imbalance, and stationary buildup
- Combines these signals into a single, explainable risk score with human-readable reasons
- Surfaces everything on a live analytics dashboard

## Detection models

SentinelX uses two purpose-fit detectors depending on scene density, both fine-tuned from Ultralytics YOLO on [CrowdHuman](https://www.crowdhuman.org/): a **person (body) model** for sparse/normal-density scenes and a **head model** for dense, heavily-occluded crowds. Full specs, training details, and benchmark numbers for both live in [`docs/TECHNICAL_REPORT.md`](docs/TECHNICAL_REPORT.md). The reasoning for using two separate detectors is in [`ARCHITECTURE.md`](ARCHITECTURE.md#why-two-detection-models).

## Tech Stack

### Module 1: Person Detection (`people_detection/`)

| Tool | Version |
|---|---|
| Python | 3.11 |
| Ultralytics (YOLO) | `>=8.3.0` |
| OpenCV (`opencv-python`) | `>=4.9.0` |
| Pillow *(fine-tuning)* | `>=10.0.0` |
| tqdm *(fine-tuning)* | `>=4.66.0` |
| huggingface_hub *(fine-tuning)* | `>=0.24.0` |
| Tracker | ByteTrack |

### Module 2: Crowd Analytics (`crowd_analysis/`)

| Tool | Version |
|---|---|
| Python | 3.11 |
| NumPy | latest stable |
| pytest | latest stable |
| Tracking algorithm | Custom greedy centroid tracker (dependency-free) |

### Module 3: Risk Prediction Engine (`risk_engine/`)

| Tool | Version |
|---|---|
| Python | 3.11 |
| FastAPI | `0.139.0` |
| Uvicorn | `0.51.0` |
| Pydantic | `2.13.4` |
| pydantic_core | `2.46.4` |
| Starlette | `1.3.1` |
| anyio | `4.14.1` |
| h11 | `0.16.0` |


### Module 4: Dashboard (`dashboard/`)

| Tool | Version |
|---|---|
| React | `^18.3.1` |
| Vite | `^5.4.8` |
| Tailwind CSS | `^3.4.13` |
| PostCSS | `^8.4.47` |
| Autoprefixer | `^10.4.20` |
| Chart.js | `^4.4.4` |

## Pipeline 

`Camera → Person/Head detector (YOLO, fine-tuned) → ByteTrack → Crowd Analytics (density/flow/entry-exit) → Risk Engine (explainable scoring) → FastAPI → React Dashboard`

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full diagram, data flow, and design decisions.

## Screenshots

<p align="center">
  <img src="ouput/risk_dense.jpg" width="90%">
</p>

<p align="center">
<b>Figure 1.</b> Risk analysis on a dense crowd scene, showing real-time people count, risk level, and contributing factors such as crowd size, slow movement, and stationary individuals.
</p>

---

<p align="center">
  <img src="ouput/risk_moderate.jpg" width="90%">
</p>

<p align="center">
<b>Figure 2.</b> Real-time crowd risk monitoring on a moderately dense scene, displaying dynamic people count, risk score, and detected behavioral indicators.
</p>

---

## Demo Video

https://drive.google.com/file/d/1FeKDpo0MTFF213wiEYRrtf67_h5EDE21/view?usp=sharing

## Getting started

**Prerequisites:** Python 3.11+, Node.js 20+, a webcam/RTSP stream/video file.

```bash
git clone https://github.com/RanjeetKaur14/SentinelX.git && cd SentinelX
 
# 1. Person detection deps
cd people_detection && pip install -r requirements.txt
 
# 2. Crowd analytics (tests)
cd ../crowd_analysis && pip install numpy pytest && pytest test/
 
# 3. Risk engine deps
cd ../risk_engine && pip install -r requirements.txt
 
# 4. Dashboard deps
cd ../dashboard && npm install
 
# 5. Integration deps (same requirements as people_detection, plus FastAPI/uvicorn)
cd ../integration && pip install -r ../people_detection/requirements.txt
```

### Running the live demo
 
Three services, each in its own terminal, **started in this order** (the dashboard calls the risk engine on startup, so bring that up first):
 
```bash
# Terminal 1 — Risk Engine API (port 8000)
cd risk_engine
uvicorn app:app --reload --host 0.0.0.0 --port 8000
 
# Terminal 2 — Detection + tracking + analytics + risk stream (port 8001)
cd integration
set SOURCE=..\people_detection\testing\datasets\videos\v1.mp4
set MODEL_PATH=..\people_detection\best.pt
set CAMERA_ID=cam_01
python -m uvicorn stream_server:app --port 8001 --reload
 
# Terminal 3 — Dashboard (port 5173)
cd dashboard
npm run dev
```

Then open **http://localhost:5173**. (`set` above is Windows `cmd`; on macOS/Linux use `export SOURCE=... MODEL_PATH=... CAMERA_ID=...` instead, same variable names.)
### Changing the video source, model, or camera ID
 
All three are read from environment variables by `integration/stream_server.py` : set them **before** starting Terminal 2 above:
 
| Variable | What it controls | Examples |
|---|---|---|
| `SOURCE` | The video feed to process | A file path (`..\people_detection\testing\datasets\videos\v1.mp4`), `0` for the default webcam, or an RTSP URL (`rtsp://<camera-ip>/stream`) |
| `MODEL_PATH` | Which detector weights to run | `..\people_detection\best.pt` (person model, default): point this at the head model's weights instead once trained for dense-crowd scenes |
| `CAMERA_ID` | Label for this feed, shown in the dashboard's camera selector | `cam_01`, `cam_02`, etc. : run a second Terminal-2 instance on a different port with a different `CAMERA_ID` to simulate multiple cameras |
 
To switch the video mid-demo: stop Terminal 2 (`Ctrl+C`), re-set `SOURCE` (and `MODEL_PATH`/`CAMERA_ID` if needed), and restart the `uvicorn stream_server:app` command. The dashboard (Terminal 3) and risk engine (Terminal 1) don't need to be restarted.
 
The dashboard itself points at the risk engine via a single line in [`dashboard/src/config.js`](dashboard/src/config.js) (`API_BASE_URL`) : change that if the risk engine runs on a different host/port (e.g. a Pi on the same network instead of `localhost`).
 
### Reproducing evaluation results (offline, no dashboard)
 
For regenerating the benchmark artifacts referenced in [`docs/EVALUATION.md`](docs/EVALUATION.md) : a single batch run over a video file, writing an annotated `.mp4` and a `risk_log.jsonl` instead of streaming live:
 
```bash
cd integration
python pipeline.py --source ../people_detection/testing/datasets/videos/v1.mp4 --model ../people_detection/best.pt --camera-id cam_01
```
 
Output goes to `integration/sentinelx_output/` (`annotated.mp4` + `risk_log.jsonl`). Add `--no-video` to skip writing the annotated video and just get the log. 

#### Sample Inputs
- `people_detection/testing/` : Benchmark images and videos.

#### Sample Outputs
- `integration/sentinelx_output/`
  - Annotated video
  - `risk_log.jsonl` (sample risk log)

## Team

| Module | Responsibilities | Author |
|---|---|---|
| Person Detection | YOLOv8n fine-tuning, live detection/tracking pipeline, benchmarking | Sriza Goel |
| Crowd Analytics | Density, heatmap, flow, entry/exit, custom edge-optimized tracker | Ranjeet Kaur |
| Risk Prediction Engine | Risk scoring model, FastAPI REST API, alerting | Khushii Duggal |
| Dashboard & Visualization | React dashboard, live risk gauge, heatmap view, alert timeline | Toyesh Gupta |

## Limitations


- Performance may decrease in extremely dense crowds with severe person occlusions.
- Detection accuracy depends on camera placement, viewing angle, and video quality.
- The system is designed as an early-warning aid and should complement, not replace, human monitoring.
- Thresholds for risk estimation may require calibration for different venues and crowd dynamics.
- Environmental conditions such as poor lighting, rain, or fog can reduce detection reliability.

## Future Scope

- Drone-based crowd monitoring
- Fire and smoke detection module
- Mobile application support
- Emergency evacuation guidance
- Digital twin visualization of venues

---

## License

Developed as part of a hackathon submission for educational and research purposes.

Original SentinelX code is released under the **MIT License** : see [`LICENSE`](./LICENSE).

<div align="center">
<br/>
<sub>SentinelX - Prevent. Protect. Predict.</sub>
</div>
