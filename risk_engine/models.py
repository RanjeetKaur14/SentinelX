from pydantic import BaseModel
from typing import List


class Analytics(BaseModel):
    people_count: int
    density: float
    average_speed: float
    opposite_flow: bool
    exit_blocked: bool
    stationary_people: int


class RiskResponse(BaseModel):
    risk_score: int
    risk_level: str
    reasons: List[str]
    alerts: List[str]