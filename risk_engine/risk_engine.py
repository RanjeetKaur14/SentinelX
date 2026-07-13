from models import Analytics


def calculate_risk(data: Analytics):
    score = 0
    reasons = []

    metrics = data.crowd_metrics

    if metrics.people_count > 150:
        score += 20
        reasons.append("Very high number of people")
    elif metrics.people_count > 80:
        score += 10
        reasons.append("Large crowd size")
    if metrics.density:
        max_zone_count = max(metrics.density.values())
        if max_zone_count > 10:
            score += 30
            reasons.append("High crowd density in a specific zone")
        elif max_zone_count > 5:
            score += 15
            reasons.append("Moderate crowd density in a specific zone")

    if metrics.average_speed > 0 and metrics.average_speed < 50:
        score += 15
        reasons.append("Crowd movement is very slow")

    if metrics.flow.label == "Mixed":
        score += 20
        reasons.append("Mixed/opposing movement detected")
    if metrics.occupancy_growth >= 3:
        score += 15
        reasons.append("Rapid occupancy growth")
    if len(metrics.stationary_tracks) > 20:
        score += 10
        reasons.append("Large number of stationary people")
    elif len(metrics.stationary_tracks) > 5 and metrics.people_count > 10:
        score += 5
        reasons.append("Noticeable number of stationary people")
    if metrics.entry_exit.total_entry - metrics.entry_exit.total_exit > 10:
        score += 10
        reasons.append("Entries far exceeding exits — crowd building up")

    if score > 100:
        score = 100
    if score >= 80:
        level = "Red"
    elif score >= 50:
        level = "Orange"
    elif score >= 25:
        level = "Yellow"
    else:
        level = "Green"

    return score, level, reasons
