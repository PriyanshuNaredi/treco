import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.agent import Agent

router = APIRouter()


class CreateAgentRequest(BaseModel):
    workspace_id: str
    name: str


class AgentResponse(BaseModel):
    id: str
    name: str
    status: str
    current_ticket_id: str | None
    workspace_id: str

    class Config:
        from_attributes = True


class CreateAgentResponse(AgentResponse):
    api_key: str  # returned only on creation, never again


@router.post("/", response_model=CreateAgentResponse)
async def create_agent(req: CreateAgentRequest, db: AsyncSession = Depends(get_db)):
    raw_key = settings.sdk_key_prefix + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    agent = Agent(
        id=str(uuid.uuid4()),
        workspace_id=req.workspace_id,
        name=req.name,
        api_key_hash=key_hash,
        status="idle",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return CreateAgentResponse(
        id=agent.id,
        name=agent.name,
        status=agent.status,
        current_ticket_id=agent.current_ticket_id,
        workspace_id=agent.workspace_id,
        api_key=raw_key,
    )


@router.get("/")
async def list_agents(workspace_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.workspace_id == workspace_id)
    )
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
