from pydantic import BaseModel
from typing import List, Dict, Optional


class Track(BaseModel):
    track_id: int
    centroid: List[float]
    speed: float
    direction: str


class FlowInfo(BaseModel):
    label: str
    confidence: float
    dominant_heading: Optional[float] = None
    entropy: float
    direction_histogram: Dict[str, int]


class EntryExitLine(BaseModel):
    entry_count: int
    exit_count: int


class EntryExit(BaseModel):
    total_entry: int
    total_exit: int
    per_line: Dict[str, EntryExitLine]


class Heatmap(BaseModel):
    fast: List[List[float]]
    slow: List[List[float]]
    trend: List[List[float]]


class CrowdMetrics(BaseModel):
    people_count: int
    average_speed: float
    occupancy_growth: float
    zone_growth: List[List[float]]
    density: Dict[str, int]
    normalized_density: Dict[str, float]
    flow: FlowInfo
    stationary_tracks: List[int]
    entry_exit: EntryExit
    heatmap: Heatmap


class Analytics(BaseModel):
    frame: int
    tracks: List[Track]
    crowd_metrics: CrowdMetrics


class RiskResponse(BaseModel):
    risk_score: int
    risk_level: str
    reasons: List[str]
    alerts: List[str]
