from fastapi import APIRouter
import json

from models import Analytics, RiskResponse
from risk_engine import calculate_risk
from alert_engine import generate_alerts
from database import save_risk_entry

router = APIRouter()


@router.post("/risk/check", response_model=RiskResponse)
def check_risk(data: Analytics):
    score, level, reasons = calculate_risk(data)
    alerts = generate_alerts(level, reasons)

    save_risk_entry({
        "input": data.dict(),
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "alerts": alerts
    })

    # Step 4: Return response
    return RiskResponse(
        risk_score=score,
        risk_level=level,
        reasons=reasons,
        alerts=alerts
    )


@router.get("/risk/sample")
def get_sample_risk():
    with open("sample_data.json") as f:
        raw_data = json.load(f)

    data = Analytics(**raw_data)
    score, level, reasons = calculate_risk(data)
    alerts = generate_alerts(level, reasons)

    return RiskResponse(
        risk_score=score,
        risk_level=level,
        reasons=reasons,
        alerts=alerts
    )
