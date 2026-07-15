# Local AI Verification

## Runs fully on-device

Everything in the core safety pipeline executes locally, with no network call in the inference path:

- Frame capture (OpenCV)
- Person/head detection (fine-tuned YOLO models, run via Ultralytics/PyTorch, or ONNX Runtime on the Pi build)
- Object tracking (ByteTrack at the detection stage; a separate NumPy-only centroid tracker in the analytics stage)
- Crowd analytics (density, flow, heatmap, entry/exit, occupancy growth) — pure Python/NumPy, no external calls
- Risk scoring (rule-based additive engine) - pure Python, no external calls
- The FastAPI REST layer (`risk`, `alerts`, `stats`, `history`) - served on the local device/LAN


None of the above requires internet connectivity to function. The system was designed to run entirely offline on a Raspberry Pi.

## Requires internet (optional, non-core)

- **Nothing in the current codebase makes an outbound internet call.** The only internet-dependent feature mentioned anywhere in the project is a *planned* future item : pushing an alert notification off-device (e.g. to a phone). If/when built, it would be the sole optional path requiring connectivity; the detection → tracking → analytics → risk pipeline would continue to function with it disabled.

## Does any user data leave the device?

**No.** Video frames are processed in memory and never uploaded, streamed, or transmitted anywhere; no data of any kind is sent to Anthropic, Ultralytics, or any other third party at inference time. (Fine-tuning was a one-time, offline training job on CrowdHuman - a training-time step, not part of the deployed runtime.)

What *is* written to local disk (derived data only: bounding boxes, counts, risk scores, never raw biometric identity), where it lives, and how long it's kept is covered in full in [`PRIVACY_AND_SAFETY.md`](PRIVACY_AND_SAFETY.md).
