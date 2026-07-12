from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import risk, alerts, stats, history

app = FastAPI(title="SentinelX - Risk Engine (Team 3)")

# Allow frontend (running on a different port) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for development; restrict this later in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect all routers
app.include_router(risk.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(history.router)


@app.get("/")
def root():
    return {"message": "SentinelX Risk Engine is running"}