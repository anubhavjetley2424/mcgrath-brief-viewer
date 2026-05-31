"""FastAPI entry point.

Run with:
    uvicorn api.main:app --reload --port 8000
from the project root (the directory containing the api/ folder).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routers import (
    activities,
    dashboard,
    deals,
    drafts,
    notifications,
    scheduled_sends,
    tasks,
)

app = FastAPI(title="McGrath Workflow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals.router)
app.include_router(drafts.router)
app.include_router(activities.router)
app.include_router(tasks.router)
app.include_router(notifications.router)
app.include_router(scheduled_sends.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
