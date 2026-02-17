from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, col, desc, or_, select

from app.database import get_session
from app.models import Agent, AuditEvent, Profile, Telemetry, TestCheck, TestRun, User
from app.services.agent_sim import write_action_telemetry, write_audit
from app.services.metrics import kpi

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request, session: Session) -> User:
    username = request.cookies.get("demo_user", "admin")
    user = session.exec(select(User).where(User.username == username)).first()
    return user or session.exec(select(User)).first()


@router.get("/")
def root():
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/switch-user")
def switch_user(name: str, request: Request):
    response = RedirectResponse(request.headers.get("referer", "/dashboard"), status_code=302)
    response.set_cookie("demo_user", name, max_age=60 * 60 * 24 * 30)
    return response


@router.get("/dashboard")
def dashboard(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    latest = session.exec(select(Telemetry).order_by(desc(Telemetry.ts)).limit(10)).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user, "kpi": kpi(session, "24h"), "latest": latest})


@router.get("/agents")
def agents_page(
    request: Request,
    search: str = "",
    status: str = "all",
    sort: str = "desc",
    agent_id: int | None = None,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    query = select(Agent)
    if search:
        query = query.where(Agent.name.contains(search))
    if status in {"online", "offline"}:
        query = query.where(Agent.status == status)
    query = query.order_by(desc(Agent.last_seen) if sort == "desc" else Agent.last_seen)
    agents = session.exec(query).all()
    selected = agent_id or (agents[0].id if agents else None)
    telemetry = []
    if selected:
        telemetry = session.exec(select(Telemetry).where(Telemetry.agent_id == selected).order_by(desc(Telemetry.ts)).limit(10)).all()
    profiles = session.exec(select(Profile)).all()
    return templates.TemplateResponse("agents.html", {"request": request, "user": user, "agents": agents, "telemetry": telemetry, "profiles": profiles, "selected": selected})


@router.post("/agents/{agent_id}/apply")
def apply_profile(agent_id: int, request: Request, profile_id: int = Form(...), session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user.role == "viewer":
        return RedirectResponse("/agents?flash=Denied", status_code=302)
    agent = session.get(Agent, agent_id)
    agent.current_profile_id = profile_id
    write_action_telemetry(session, agent, "apply_profile")
    write_audit(session, user, "APPLY_PROFILE", agent_id, details=f"profile={profile_id}")
    session.commit()
    return RedirectResponse("/agents?flash=Profile+applied", status_code=302)


@router.post("/agents/{agent_id}/stop")
def stop_profile(agent_id: int, request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user.role == "viewer":
        return RedirectResponse("/agents?flash=Denied", status_code=302)
    agent = session.get(Agent, agent_id)
    agent.current_profile_id = None
    write_action_telemetry(session, agent, "stop_profile")
    write_audit(session, user, "STOP_PROFILE", agent_id)
    session.commit()
    return RedirectResponse("/agents?flash=Profile+stopped", status_code=302)


@router.get("/profiles")
def profiles_page(request: Request, search: str = "", sort: str = "name", session: Session = Depends(get_session)):
    user = current_user(request, session)
    query = select(Profile)
    if search:
        query = query.where(Profile.name.contains(search))
    query = query.order_by(Profile.name if sort == "name" else desc(Profile.created_at))
    profiles = session.exec(query).all()
    return templates.TemplateResponse("profiles.html", {"request": request, "user": user, "profiles": profiles})


@router.get("/audit")
def audit_page(
    request: Request,
    username: str = "",
    action: str = "",
    from_date: str = "",
    to_date: str = "",
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    query = select(AuditEvent)
    if username:
        query = query.where(AuditEvent.username.contains(username))
    if action:
        query = query.where(AuditEvent.action.contains(action))
    if from_date:
        query = query.where(AuditEvent.ts >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.where(AuditEvent.ts <= datetime.fromisoformat(to_date))
    rows = session.exec(query.order_by(desc(AuditEvent.ts)).limit(200)).all()
    return templates.TemplateResponse("audit.html", {"request": request, "user": user, "rows": rows})


@router.get("/analytics")
def analytics_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    events = session.exec(select(AuditEvent).order_by(desc(AuditEvent.ts)).limit(25)).all()
    telemetry = session.exec(select(Telemetry).order_by(desc(Telemetry.ts)).limit(25)).all()
    merged = sorted([
        {"ts": e.ts, "type": "audit", "action": e.action, "details": e.details or e.username} for e in events
    ] + [
        {"ts": t.ts, "type": "telemetry", "action": t.scenario, "details": f"lat={t.latency_ms} err={t.errors}"} for t in telemetry
    ], key=lambda x: x["ts"], reverse=True)[:50]
    return templates.TemplateResponse("analytics.html", {"request": request, "user": user, "events": merged, "kpi": kpi(session, "24h")})


@router.get("/tests")
def tests_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    runs = session.exec(select(TestRun).order_by(desc(TestRun.ts)).limit(30)).all()
    checks = {}
    if runs:
        run_ids = [r.id for r in runs]
        for check in session.exec(select(TestCheck).where(col(TestCheck.test_run_id).in_(run_ids))).all():
            checks.setdefault(check.test_run_id, []).append(check)
    runs_chart = [{"ts": r.ts.isoformat(), "status": r.status} for r in runs]
    return templates.TemplateResponse("tests.html", {"request": request, "user": user, "runs": runs, "checks": checks, "runs_chart": runs_chart})
