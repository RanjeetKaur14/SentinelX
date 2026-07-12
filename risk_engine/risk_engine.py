from models import Analytics


def calculate_risk(data: Analytics):
    score = 0
    reasons = []

    # Rule 1: Crowd density
    if data.density > 0.7:
        score += 30
        reasons.append("High crowd density")
    elif data.density > 0.5:
        score += 15
        reasons.append("Moderate crowd density")

    # Rule 2: People count
    if data.people_count > 150:
        score += 20
        reasons.append("Very high number of people")
    elif data.people_count > 80:
        score += 10
        reasons.append("Large crowd size")

    # Rule 3: Average speed (low speed = people stuck/not moving = risky)
    if data.average_speed < 0.5:
        score += 15
        reasons.append("Crowd movement is very slow")

    # Rule 4: Opposite flow (people walking into each other)
    if data.opposite_flow:
        score += 20
        reasons.append("Opposing movement detected")

    # Rule 5: Exit blocked (very dangerous)
    if data.exit_blocked:
        score += 25
        reasons.append("Exit blocked")

    # Rule 6: Stationary people (people not moving at all in a crowd)
    if data.stationary_people > 20:
        score += 10
        reasons.append("Large number of stationary people")

    # Cap score at 100
    if score > 100:
        score = 100

    # Decide risk level based on score
    if score >= 80:
        level = "Red"
    elif score >= 50:
        level = "Orange"
    elif score >= 25:
        level = "Yellow"
    else:
        level = "Green"

    return score, level, reasons