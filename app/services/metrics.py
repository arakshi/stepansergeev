from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlmodel import Session, func, select

from app.models import Agent, AuditEvent, Profile, Telemetry


def _range_start(range_value: str) -> datetime:
    now = datetime.utcnow()
    mapping = {"1h": timedelta(hours=1), "24h": timedelta(hours=24), "7d": timedelta(days=7)}
    return now - mapping.get(range_value, timedelta(hours=24))


def kpi(session: Session, range_value: str = "24h") -> dict:
    start = _range_start(range_value)
    total_agents = len(session.exec(select(Agent)).all())
    online_agents = len(session.exec(select(Agent).where(Agent.status == "online")).all())
    deploys = len(
        session.exec(
            select(AuditEvent).where(AuditEvent.action == "APPLY_PROFILE", AuditEvent.ts >= datetime.utcnow() - timedelta(hours=24))
        ).all()
    )
    telemetry = session.exec(select(Telemetry).where(Telemetry.ts >= start)).all()
    total = len(telemetry) or 1
    errors = sum(t.errors for t in telemetry)
    avg_latency = round(sum(t.latency_ms for t in telemetry) / total, 2)

    return {
        "online_agents": online_agents,
        "total_agents": total_agents,
        "deployments_24h": deploys,
        "error_rate_per_1000": round(errors * 1000 / total, 2),
        "avg_latency": avg_latency,
    }


def traffic_timeseries(session: Session, range_value: str = "1h") -> list[dict]:
    start = _range_start(range_value)
    rows = session.exec(select(Telemetry).where(Telemetry.ts >= start).order_by(Telemetry.ts)).all()
    bucket: dict[str, dict] = {}
    for row in rows:
        key = row.ts.strftime("%Y-%m-%d %H:%M")
        if key not in bucket:
            bucket[key] = {"ts": key, "bytes_in": 0, "bytes_out": 0, "latency_total": 0, "count": 0}
        bucket[key]["bytes_in"] += row.bytes_in
        bucket[key]["bytes_out"] += row.bytes_out
        bucket[key]["latency_total"] += row.latency_ms
        bucket[key]["count"] += 1
    return list(bucket.values())


def latency_timeseries(session: Session, range_value: str = "1h") -> list[dict]:
    traffic = traffic_timeseries(session, range_value)
    return [{"ts": row["ts"], "latency_ms": round(row["latency_total"] / row["count"], 2)} for row in traffic if row["count"]]


def actions_breakdown(session: Session, range_value: str = "24h") -> dict:
    start = _range_start(range_value)
    rows = session.exec(select(AuditEvent).where(AuditEvent.ts >= start)).all()
    result = {"PING": 0, "APPLY": 0, "STOP": 0}
    for row in rows:
        if row.action.startswith("PING"):
            result["PING"] += 1
        if row.action == "APPLY_PROFILE":
            result["APPLY"] += 1
        if row.action == "STOP_PROFILE":
            result["STOP"] += 1
    return result


def profile_distribution(session: Session, range_value: str = "7d") -> list[dict]:
    start = _range_start(range_value)
    rows = session.exec(
        select(Telemetry.profile_id, func.count(Telemetry.id)).where(Telemetry.ts >= start, Telemetry.scenario == "apply_profile").group_by(Telemetry.profile_id)
    ).all()
    profiles = {p.id: p.name for p in session.exec(select(Profile)).all()}
    named = [{"label": profiles.get(pid, "unknown"), "value": count} for pid, count in rows if pid is not None]
    named.sort(key=lambda x: x["value"], reverse=True)
    if len(named) > 5:
        other = sum(x["value"] for x in named[5:])
        named = named[:5] + [{"label": "other", "value": other}]
    return named


def top_errors(session: Session, range_value: str = "24h") -> list[dict]:
    start = _range_start(range_value)
    rows = session.exec(
        select(Telemetry.agent_id, func.sum(Telemetry.errors))
        .where(Telemetry.ts >= start)
        .group_by(Telemetry.agent_id)
        .order_by(func.sum(Telemetry.errors).desc())
        .limit(5)
    ).all()
    agents = {a.id: a.name for a in session.exec(select(Agent)).all()}
    return [{"agent": agents.get(agent_id, f"agent-{agent_id}"), "errors": int(errors or 0)} for agent_id, errors in rows]
