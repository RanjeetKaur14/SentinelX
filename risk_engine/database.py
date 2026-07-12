# Simple in-memory storage (temporary, resets when server restarts)
# Later this can be replaced with a real database (SQLite/PostgreSQL)

risk_history = []


def save_risk_entry(entry: dict):
    risk_history.append(entry)
    # Keep only last 50 entries so it doesn't grow forever
    if len(risk_history) > 50:
        risk_history.pop(0)


def get_all_history():
    return risk_history


def get_latest_entry():
    if risk_history:
        return risk_history[-1]
    return None