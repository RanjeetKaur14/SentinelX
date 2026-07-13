# SentinelX

**Prevent. Protect. Predict.**

SentinelX is an **Edge AI-powered Crowd Monitoring and Stampede Prevention System** designed to transform existing CCTV cameras into intelligent safety systems. Instead of simply recording footage, SentinelX continuously analyzes crowd behavior in real time to detect potentially dangerous situations and generate early alerts before a stampede or crowd disaster occurs.

The system performs AI inference locally on edge devices, ensuring **low latency**, **privacy preservation**, **reduced operational costs**, and **no dependency on cloud connectivity**.

---

## Problem Statement

Large public gatherings such as railway stations, metro stations, temples, stadiums, concerts, shopping malls, festivals, and college events often become overcrowded. Traditional CCTV systems are reactive—they record incidents but do not help prevent them.

Monitoring dozens of live camera feeds simultaneously is difficult for security personnel, making it challenging to identify hazardous crowd conditions before they escalate into emergencies.

SentinelX addresses this challenge by providing real-time crowd intelligence and proactive risk prediction.

---

## Features

- Real-time person detection
- Multi-object tracking
- Crowd density estimation
- Movement flow analysis
- Congestion detection
- Exit blockage monitoring
- Crowd risk prediction
- Smart alert generation
- Live analytics dashboard
- Edge AI deployment

---

## AI Workflow

```
Camera
      ↓
Frame Capture
      ↓
YOLO Person Detection
      ↓
ByteTrack Tracking
      ↓
Crowd Analytics
      ↓
Risk Prediction Engine
      ↓
Smart Alert Generation
      ↓
Live Dashboard
```

---

## Technology Stack

### AI & Computer Vision

- YOLOv11n
- ByteTrack
- OpenCV
- ONNX Runtime
- OpenVINO (Optional)

### Backend

- FastAPI
- SQLite

### Frontend

- React
- Tailwind CSS
- Chart.js

### Deployment

- Laptop
- Raspberry Pi
- Intel NUC
- NVIDIA Jetson Nano

---

## Project Modules

### Module 1 – Person Detection

**Author:** Sriza Goel

Responsibilities:

- YOLOv11n person detection
- Person counting
- Real-time occupancy estimation
- Frame processing

---

### Module 2 – Crowd Analytics

**Author:** Ranjeet Kaur 

Responsibilities:

- ByteTrack multi-object tracking
- Crowd density estimation
- Heatmap generation
- Movement flow analysis
- Congestion analysis
- Crowd behavior analytics

---

### Module 3 – Risk Prediction Engine

**Author:** Khushii Duggal

Responsibilities:

- Crowd risk assessment
- Risk score calculation
- Risk level classification
- Alert generation
- SQLite database management
- FastAPI REST APIs
- Crowd analytics history

---

### Module 4 – Dashboard & Visualization

**Author:** Toyesh Gupta

Responsibilities:

- React dashboard
- Live camera visualization
- Risk dashboard
- Charts and analytics
- Alert timeline
- User Interface

---

## Inputs

- CCTV Camera
- Webcam
- Recorded Video

---

## Outputs

- People Count
- Crowd Density
- Heatmaps
- Risk Score
- Smart Alerts
- Live Dashboard
- Crowd Analytics

---

## Risk Factors

The risk prediction engine evaluates multiple crowd parameters instead of relying solely on crowd count.

These include:

- Number of people
- Crowd density
- Average movement speed
- Movement direction
- Opposing movement
- Congestion level
- Exit blockage
- Stationary crowd buildup

These factors are combined to calculate a dynamic crowd risk score.

---

## Expected Outcomes

- Early crowd congestion detection
- Stampede risk prediction
- Real-time alerts
- Privacy-preserving surveillance
- Low-latency edge AI inference
- Improved public safety

---

## Future Scope

- Multi-camera tracking
- Drone-based crowd monitoring
- Fire and smoke detection
- Mobile application support
- Emergency evacuation guidance
- Digital twin visualization
- Edge-to-edge camera collaboration

---

## Repository Structure

```
SentinelX/
│
├── Detection Module
├── Crowd Analytics Module
├── Risk Prediction Module
├── Dashboard Module
└── Documentation
```

---

## Team

| Team Member | Module |
|------------|-------------------------------|
| **Sriza Goel** | Person Detection |
| **Ranjeet Kaur** | Crowd Analytics |
| **Khushii Duggal** | Risk Prediction Engine |
| **Toyesh Gupta** | Dashboard & Visualization |

---

## License

This project was developed as part of a Hackathon submission for educational and research purposes.
