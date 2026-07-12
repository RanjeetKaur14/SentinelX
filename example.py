"""
example.py
----------
Standalone demo: simulates a short stream of frames (a handful of
people walking through a scene, some crossing a virtual entry line)
and prints the analytics JSON produced for each frame.

Run:
    python example.py
"""

import json
import math
import random

from analytics import AnalyticsEngine, EngineConfig, EntryExitConfig, EntryExitLine
from analytics.config import TrackerConfig, DensityConfig, FlowConfig


def make_bbox(cx: float, cy: float, w: float = 60, h: float = 160):
    """Build an (x1, y1, x2, y2) box centered at (cx, cy)."""
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def simulate_frames(num_frames: int = 40, num_people: int = 6):
    """
    Generates a synthetic stream of frame payloads matching the input
    spec: a handful of people drifting left-to-right across a
    1920x1080 frame, crossing a vertical line near the middle.
    """
    random.seed(42)
    image_w, image_h = 1920, 1080

    # Each simulated person starts at a random x offset and constant y,
    # moving rightward at a slightly randomized speed -- enough to
    # exercise tracking, velocity, direction, and entry/exit counting.
    people = [
        {
            "start_x": random.uniform(-200, 100),
            "y": random.uniform(150, image_h - 150),
            "speed": random.uniform(8, 14),
        }
        for _ in range(num_people)
    ]

    frames = []
    for frame_idx in range(num_frames):
        detections = []
        for person in people:
            cx = person["start_x"] + person["speed"] * frame_idx
            cy = person["y"]
            if -50 <= cx <= image_w + 50:
                detections.append(
                    {"bbox": make_bbox(cx, cy), "confidence": round(random.uniform(0.85, 0.99), 2)}
                )

        frames.append(
            {
                "frame": frame_idx,
                "timestamp": 1721234567.0 + frame_idx * 0.033,  # ~30 FPS
                "camera_id": "cam01",
                "image_size": {"width": image_w, "height": image_h},
                "detections": detections,
            }
        )

    return frames


def main():
    config = EngineConfig(
        tracker=TrackerConfig(max_match_distance=150.0, max_disappeared_frames=10),
        density=DensityConfig(grid_rows=4, grid_cols=4),
        flow=FlowConfig(min_moving_tracks=2),
        entry_exit=EntryExitConfig(
            lines=(
                EntryExitLine(
                    name="mid_line",
                    p1=(150, 0),
                    p2=(150, 1080),
                    direction_in="left_to_right",
                ),
            )
        ),
    )

    engine = AnalyticsEngine(config)
    frames = simulate_frames(num_frames=40, num_people=6)

    for payload in frames:
        result = engine.process_frame(payload)
        cm = result["crowd_metrics"]

        # Print a compact summary per frame, and the full JSON for a
        # couple of representative frames so the output shape is clear.
        print(
            f"frame={result['frame']:>3}  "
            f"people={cm['people_count']:>2}  "
            f"entries={cm['entry_exit']['total_entry']:>2}  "
            f"exits={cm['entry_exit']['total_exit']:>2}  "
            f"occupancy_growth={cm['occupancy_growth']:>5.1f}  "
            f"flow={cm['flow']['label']:>8}  "
            f"flow_conf={cm['flow']['confidence']:.2f}  "
            f"stationary={len(cm['stationary_tracks'])}"
        )

        if result["frame"] in (0, 20, 39):
            print(json.dumps(result, indent=2))
            print("-" * 70)

    print("\nFinal rolling (decayed) heatmap:")
    for row in engine.rolling_heatmap:
        print(row)

    print(f"\nAnalytics buffer length: {len(engine.analytics_buffer)}")
    print(f"Active tracks at end: {engine.active_track_count}")


if __name__ == "__main__":
    main()
