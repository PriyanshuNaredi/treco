import hashlib
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.agent import Agent
from app.models.event import AgentEvent

router = APIRouter()


class EventRequest(BaseModel):
    ticket_id: str
    event_type: Literal["ticket_started", "criterion_checked", "criterion_failed", "pr_opened", "done", "error", "log"]
    criterion_id: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: str | None = None
    payload: dict = {}


class CostSummary(BaseModel):
    ticket_id: str
    total_tokens_in: int
    total_tokens_out: int
    event_count: int


async def _resolve_agent(api_key: str, db: AsyncSession) -> Agent:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(select(Agent).where(Agent.api_key_hash == key_hash))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid agent API key")
    return agent


@router.post("/")
async def post_event(
    req: EventRequest,
    x_agent_key: str = Header(..., alias="X-Agent-Key"),
    db: AsyncSession = Depends(get_db),
):
    agent = await _resolve_agent(x_agent_key, db)

    event = AgentEvent(
        id=str(uuid.uuid4()),
        agent_id=agent.id,
        ticket_id=req.ticket_id,
        workspace_id=agent.workspace_id,
        event_type=req.event_type,
        criterion_id=req.criterion_id,
        tokens_in=req.tokens_in,
        tokens_out=req.tokens_out,
        model=req.model,
        payload=req.payload,
    )
    db.add(event)

    if req.event_type == "ticket_started":
        agent.status = "working"
        agent.current_ticket_id = req.ticket_id
    elif req.event_type in ("done", "error"):
        agent.status = "idle" if req.event_type == "done" else "error"
        agent.current_ticket_id = None

    await db.commit()
    return {"id": event.id}


@router.get("/ticket/{ticket_id}")
async def get_ticket_events(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentEvent)
        .where(AgentEvent.ticket_id == ticket_id)
        .order_by(AgentEvent.created_at)
    )
    return result.scalars().all()


@router.get("/ticket/{ticket_id}/cost", response_model=CostSummary)
async def get_ticket_cost(ticket_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.sum(AgentEvent.tokens_in),
            func.sum(AgentEvent.tokens_out),
            func.count(AgentEvent.id),
        ).where(AgentEvent.ticket_id == ticket_id)
    )
    tokens_in, tokens_out, count = result.one()
    return CostSummary(
        ticket_id=ticket_id,
        total_tokens_in=tokens_in or 0,
        total_tokens_out=tokens_out or 0,
        event_count=count or 0,
    )
