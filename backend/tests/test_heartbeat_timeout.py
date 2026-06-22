"""Tests for the heartbeat-timeout background task (_mark_stuck_agents)."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

from app.core.constants import AgentStatus
from app.main import _mark_stuck_agents
from app.models.agent import Agent
from app.models.event import AgentEvent
from tests.shared import TestSessionLocal


def _make_agent(
    *,
    status: str = AgentStatus.WORKING,
    last_seen_at: datetime | None = None,
    workspace_id: str = "ws1",
    ticket_id: str | None = None,
) -> Agent:
    raw = "treco_" + secrets.token_urlsafe(16)
    return Agent(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        name="test-agent",
        api_key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        status=status,
        current_ticket_id=ticket_id,
        last_seen_at=last_seen_at,
    )


@pytest_asyncio.fixture
async def db():
    async with TestSessionLocal() as session:
        yield session


_CUTOFF = datetime.utcnow() - timedelta(minutes=5)


class TestMarkStuckAgents:
    @pytest.mark.asyncio
    async def test_silent_working_agent_goes_offline(self, db):
        agent = _make_agent(last_seen_at=datetime.utcnow() - timedelta(minutes=10))
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        await db.refresh(agent)
        assert agent.status == AgentStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_silent_working_agent_emits_deviation(self, db):
        ticket_id = str(uuid.uuid4())
        agent = _make_agent(
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
            ticket_id=ticket_id,
        )
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        from sqlalchemy import select
        result = await db.execute(
            select(AgentEvent)
            .where(AgentEvent.agent_id == agent.id)
            .where(AgentEvent.event_type == "deviation")
        )
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].payload["deviation_type"] == "stuck"

    @pytest.mark.asyncio
    async def test_agent_with_null_last_seen_goes_offline(self, db):
        agent = _make_agent(last_seen_at=None)
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        await db.refresh(agent)
        assert agent.status == AgentStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_active_agent_not_marked_offline(self, db):
        agent = _make_agent(last_seen_at=datetime.utcnow() - timedelta(minutes=1))
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        await db.refresh(agent)
        assert agent.status == AgentStatus.WORKING

    @pytest.mark.asyncio
    async def test_idle_agent_not_affected(self, db):
        agent = _make_agent(
            status=AgentStatus.IDLE,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
        )
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        await db.refresh(agent)
        assert agent.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_offline_agent_not_re_processed(self, db):
        agent = _make_agent(
            status=AgentStatus.OFFLINE,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
        )
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        from sqlalchemy import select
        result = await db.execute(
            select(AgentEvent).where(AgentEvent.agent_id == agent.id)
        )
        assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_deviation_not_spammed_when_recent_exists(self, db):
        ticket_id = str(uuid.uuid4())
        agent = _make_agent(
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
            ticket_id=ticket_id,
        )
        db.add(agent)
        await db.commit()

        # Pre-existing deviation emitted within the cutoff window
        db.add(AgentEvent(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            ticket_id=ticket_id,
            workspace_id=agent.workspace_id,
            event_type="deviation",
            payload={"deviation_type": "stuck"},
        ))
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        from sqlalchemy import select
        result = await db.execute(
            select(AgentEvent)
            .where(AgentEvent.agent_id == agent.id)
            .where(AgentEvent.event_type == "deviation")
        )
        # Status goes offline but no second deviation event
        assert len(result.scalars().all()) == 1
        await db.refresh(agent)
        assert agent.status == AgentStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_error_agent_not_affected(self, db):
        agent = _make_agent(
            status=AgentStatus.ERROR,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
        )
        db.add(agent)
        await db.commit()

        await _mark_stuck_agents(db, _CUTOFF)
        await db.commit()

        await db.refresh(agent)
        assert agent.status == AgentStatus.ERROR
