from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .models import Agent, AuditEvent, Profile, Telemetry, TestCheck, TestRun, User


USERS = [
    ("admin", "admin"),
    ("operator", "operator"),
    ("viewer", "viewer"),
]

PROFILES = [
    ("Balanced", "balanced", 0, 0, 0),
    ("Low Latency", "performance", -15, 1, 20),
    ("Stable", "reliability", 15, -2, -10),
    ("Throughput", "throughput", 5, 2, 35),
    ("Diagnostics", "diagnostic", 30, 3, -20),
]


AGENT_NAMES = [
    "edge-node-1",
    "edge-node-2",
    "core-proxy-1",
    "core-proxy-2",
    "staging-gw-1",
    "mobile-relay-1",
    "sandbox-agent",
]


def seed_if_needed(session: Session) -> None:
    if session.exec(select(User)).first():
        return

    users = [User(username=u, role=r) for u, r in USERS]
    profiles = [
        Profile(
            name=name,
            mode=mode,
            latency_modifier=lat,
            error_modifier=err,
            throughput_modifier=thr,
        )
        for name, mode, lat, err, thr in PROFILES
    ]
    session.add_all(users + profiles)
    session.flush()

    agents = []
    for name in AGENT_NAMES:
        profile = random.choice(profiles + [None])
        agents.append(
            Agent(
                name=name,
                status=random.choice(["online", "online", "offline"]),
                last_seen=datetime.utcnow() - timedelta(minutes=random.randint(0, 20)),
                current_profile_id=profile.id if profile else None,
            )
        )
    session.add_all(agents)
    session.flush()

    admin = users[0]
    for agent in agents:
        session.add(
            AuditEvent(
                user_id=admin.id,
                username=admin.username,
                action="SEED_CREATE_AGENT",
                target_id=agent.id,
                details="Initial seed",
            )
        )

    now = datetime.utcnow()
    for minute in range(60, 0, -1):
        ts = now - timedelta(minutes=minute)
        for agent in agents:
            if agent.status == "offline" and random.random() < 0.7:
                continue
            profile = next((p for p in profiles if p.id == agent.current_profile_id), None)
            latency_base = 70 + (profile.latency_modifier if profile else 0)
            err_base = max(0, 1 + (profile.error_modifier if profile else 0))
            thr_base = 800 + (profile.throughput_modifier if profile else 0) * 12
            session.add(
                Telemetry(
                    ts=ts,
                    agent_id=agent.id,
                    bytes_in=max(100, int(random.gauss(thr_base, 130))),
                    bytes_out=max(100, int(random.gauss(thr_base * 0.8, 120))),
                    latency_ms=max(20, int(random.gauss(latency_base, 10))),
                    errors=max(0, int(random.random() < (err_base / 20))),
                    profile_id=agent.current_profile_id,
                    scenario="heartbeat",
                )
            )

    for day in range(14, -1, -1):
        runs = random.randint(3, 8)
        date_base = now - timedelta(days=day)
        for _ in range(runs):
            status = random.choice(["passed", "passed", "failed"])
            run = TestRun(
                ts=date_base + timedelta(minutes=random.randint(0, 1200)),
                status=status,
                duration_ms=random.randint(500, 4000),
                profile_id=random.choice(profiles).id,
            )
            session.add(run)
            session.flush()
            checks = ["connectivity", "handshake", "latency-budget", "error-budget"]
            for check in checks:
                c_status = "passed" if status == "passed" or random.random() > 0.2 else "failed"
                session.add(
                    TestCheck(
                        test_run_id=run.id,
                        check_name=check,
                        status=c_status,
                        message="ok" if c_status == "passed" else "threshold exceeded",
                    )
                )

    session.commit()
