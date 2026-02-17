import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import engine, init_db
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.seed import seed_if_needed
from app.services.agent_sim import telemetry_loop
from sqlmodel import Session

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
