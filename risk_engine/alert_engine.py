def generate_alerts(risk_level: str, reasons: list):
    alerts = []

    if risk_level == "Red":
        alerts.append("Critical Alert: Immediate action required")
        alerts.append("Notify emergency response team")

    elif risk_level == "Orange":
        alerts.append("Congestion Warning: Monitor closely")

    elif risk_level == "Yellow":
        alerts.append("Caution: Crowd building up")

    else:
        alerts.append("Situation normal")

    # Add specific alerts based on reasons
    if "Exit blocked" in reasons:
        alerts.append("Send team to clear blocked exit")

    if "Opposing movement detected" in reasons:
        alerts.append("Deploy crowd control to manage flow")

    return alerts