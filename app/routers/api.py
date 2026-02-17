from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import Telemetry
from app.services.metrics import actions_breakdown, kpi, latency_timeseries, profile_distribution, top_errors, traffic_timeseries

router = APIRouter(prefix="/api", tags=["api"])


def _start(range_value: str) -> datetime:
    return datetime.utcnow() - {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}.get(range_value, timedelta(hours=24))


@router.get("/metrics/kpi")
def get_kpi(range: str = Query("24h"), session: Session = Depends(get_session)):
    return JSONResponse(kpi(session, range))


@router.get("/metrics/traffic")
def get_traffic(range: str = Query("1h"), session: Session = Depends(get_session)):
    return JSONResponse(traffic_timeseries(session, range))


@router.get("/metrics/latency")
def get_latency(range: str = Query("1h"), session: Session = Depends(get_session)):
    return JSONResponse(latency_timeseries(session, range))


@router.get("/metrics/actions")
def get_actions(range: str = Query("24h"), session: Session = Depends(get_session)):
    return JSONResponse(actions_breakdown(session, range))


@router.get("/metrics/profile_distribution")
def get_profile_distribution(range: str = Query("7d"), session: Session = Depends(get_session)):
    return JSONResponse(profile_distribution(session, range))


@router.get("/metrics/top_errors")
def get_top_errors(range: str = Query("24h"), session: Session = Depends(get_session)):
    return JSONResponse(top_errors(session, range))


@router.get("/telemetry/export.csv")
def export_csv(range: str = Query("24h"), session: Session = Depends(get_session)):
    rows = session.exec(select(Telemetry).where(Telemetry.ts >= _start(range)).order_by(Telemetry.ts.desc())).all()
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(["ts", "agent_id", "bytes_in", "bytes_out", "latency_ms", "errors", "profile_id", "scenario"])
    for row in rows:
        writer.writerow([row.ts.isoformat(), row.agent_id, row.bytes_in, row.bytes_out, row.latency_ms, row.errors, row.profile_id, row.scenario])
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=telemetry.csv"})
