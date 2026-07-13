from fastapi import APIRouter
from database import get_all_history

router = APIRouter()


@router.get("/stats/summary")
def stats_summary():
    history = get_all_history()

    if not history:
        return {"message": "No data yet"}

    total_checks = len(history)
    red_count = sum(1 for h in history if h["risk_level"] == "Red")
    orange_count = sum(1 for h in history if h["risk_level"] == "Orange")
    yellow_count = sum(1 for h in history if h["risk_level"] == "Yellow")
    green_count = sum(1 for h in history if h["risk_level"] == "Green")

    return {
        "total_checks": total_checks,
        "red_count": red_count,
        "orange_count": orange_count,
        "yellow_count": yellow_count,
        "green_count": green_count,
        "latest_risk_level": history[-1]["risk_level"]
    }
