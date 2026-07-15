from fastapi import APIRouter
from database import get_latest_entry

router = APIRouter()


@router.get("/alerts/latest")
def latest_alerts():
    entry = get_latest_entry()
    if entry is None:
        return {"alerts": [], "message": "No data yet"}
    return {"alerts": entry["alerts"]}
