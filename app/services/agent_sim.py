from __future__ import annotations

import asyncio
import random
from datetime import datetime

from sqlmodel import Session, select

from app.database import engine
from app.models import Agent, AuditEvent, Profile, Telemetry, User


async def telemetry_loop(interval_s: int = 7) -> None:
    while True:
        with Session(engine) as session:
            generate_heartbeat(session)
            session.commit()
        await asyncio.sleep(interval_s)


def generate_heartbeat(session: Session) -> None:
    profiles = {p.id: p for p in session.exec(select(Profile)).all()}
    online_agents = session.exec(select(Agent).where(Agent.status == "online")).all()
    now = datetime.utcnow()
    for agent in online_agents:
        profile = profiles.get(agent.current_profile_id)
        latency_base = 65 + (profile.latency_modifier if profile else 0)
        error_base = max(0, 1 + (profile.error_modifier if profile else 0))
        throughput = 900 + ((profile.throughput_modifier if profile else 0) * 8)
        session.add(
            Telemetry(
                ts=now,
                agent_id=agent.id,
                bytes_in=max(100, int(random.gauss(throughput, 140))),
                bytes_out=max(100, int(random.gauss(throughput * 0.75, 120))),
                latency_ms=max(15, int(random.gauss(latency_base, 12))),
                errors=max(0, int(random.random() < (error_base / 30))),
                profile_id=agent.current_profile_id,
                scenario="heartbeat",
            )
        )
        agent.last_seen = now


def write_action_telemetry(session: Session, agent: Agent, scenario: str) -> None:
    profile = session.get(Profile, agent.current_profile_id) if agent.current_profile_id else None
    session.add(
        Telemetry(
            ts=datetime.utcnow(),
            agent_id=agent.id,
            bytes_in=random.randint(50, 200),
            bytes_out=random.randint(50, 200),
            latency_ms=max(20, 70 + (profile.latency_modifier if profile else 0) + random.randint(-10, 10)),
            errors=max(0, random.randint(0, 1) + (profile.error_modifier if profile else 0)),
            profile_id=agent.current_profile_id,
            scenario=scenario,
        )
    )


def write_audit(session: Session, user: User, action: str, target_id: int, details: str = "") -> None:
    session.add(
        AuditEvent(
            user_id=user.id,
            username=user.username,
            action=action,
            target_id=target_id,
            details=details,
        )
    )
