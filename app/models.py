from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    role: str = Field(default="viewer", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Profile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    mode: str = Field(default="balanced")
    latency_modifier: int = Field(default=0)
    error_modifier: int = Field(default=0)
    throughput_modifier: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    status: str = Field(default="online", index=True)
    last_seen: datetime = Field(default_factory=datetime.utcnow, index=True)
    current_profile_id: Optional[int] = Field(default=None, foreign_key="profile.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    username: str = Field(index=True)
    action: str = Field(index=True)
    target_type: str = Field(default="agent")
    target_id: Optional[int] = Field(default=None)
    details: str = Field(default="")


class Telemetry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    bytes_in: int = Field(default=0)
    bytes_out: int = Field(default=0)
    latency_ms: int = Field(default=0)
    errors: int = Field(default=0)
    profile_id: Optional[int] = Field(default=None, foreign_key="profile.id", index=True)
    scenario: str = Field(default="heartbeat", index=True)


class TestRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    profile_id: Optional[int] = Field(default=None, foreign_key="profile.id")
    status: str = Field(default="passed", index=True)
    duration_ms: int = Field(default=0)


class TestCheck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    test_run_id: int = Field(foreign_key="testrun.id", index=True)
    check_name: str = Field(index=True)
    status: str = Field(default="passed")
    message: str = Field(default="")
