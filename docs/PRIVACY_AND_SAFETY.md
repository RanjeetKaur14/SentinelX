# Privacy and Safety

## Data handling

- Video frames are read from the camera/video source, run through detection and tracking in memory, and then discarded, the raw frame itself is not retained after processing.
- Only **derived, non-biometric** data is produced: bounding-box coordinates, detection confidence, short-lived track IDs, per-frame people counts, aggregated crowd metrics (density, flow, entry/exit), and the resulting risk score/reasons.
- No facial recognition, face embeddings, gait/re-identification, or any other biometric identification technique is used anywhere in the pipeline. Tracking is frame-to-frame positional association only, not persistent identity across sessions.

## Storage

| Artifact | Location | Purpose | Persistence |
|---|---|---|---|
| Per-frame detection JSON (`latest_frame.json`, `session_log.jsonl`) | `people_detection/output/` | Demo/debug output of the detection stage | Local disk, grows with each run|
| Annotated video + risk log (`annotated.mp4`, `risk_log.jsonl`) | `integration/sentinelx_output/` | Demo/debug output of the full pipeline | Local disk |
| Risk history | In-memory Python list (`risk_engine/database.py`) | Serves the `/history` and `/stats` API endpoints | Capped at the last 50 entries; lost on process restart, never written to a database or disk |


## Permissions

The system needs access to a camera or video stream only. It does not require, and does not request, microphone access, contacts, or any other device permission as of now.

## Limitations and potential risks

- **Presence data is still sensitive, even without identity.** Bounding-box coordinates and timestamps of individuals in a monitored area can be considered personal data in some jurisdictions, even though SentinelX performs no identification. Venues deploying this should apply their own signage/consent and data-retention policy for camera coverage, consistent with local regulation.
- **Not a certified safety system.** SentinelX is explicitly designed as an early-warning aid to complement, not replace, human monitoring and existing safety procedures. This should be communicated clearly to any venue operator using it. Detection accuracy, known failure modes, and risk-threshold calibration status are catalogued in [`EVALUATION.md`](EVALUATION.md), but the practical implication for deployment is: keep a human operator in the loop, don't act on risk scores autonomously.

