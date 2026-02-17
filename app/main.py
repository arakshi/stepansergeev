from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Позволяет запускать файл напрямую: python app/main.py
# (иначе в Windows/PyCharm может подхватиться внешний пакет `app` из site-packages)
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.database import engine, init_db
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.seed import seed_if_needed
from app.services.agent_sim import telemetry_loop

app = FastAPI(title="Simulation Control Panel")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(pages_router)
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    init_db()
    with Session(engine) as session:
        seed_if_needed(session)
    asyncio.create_task(telemetry_loop())


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
