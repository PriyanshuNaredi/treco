import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.ticket import Ticket
from app.services.adapters import ADAPTERS
from app.services.criteria_extractor import extract_criteria

router = APIRouter()


class ImportTicketRequest(BaseModel):
    source: Literal["jira", "linear", "asana", "github"]
    workspace_id: str
    raw: dict[str, Any]


class CreateTicketRequest(BaseModel):
    workspace_id: str
    title: str
    description: str | None = None
    acceptance_criteria: list[str] = []


class TicketResponse(BaseModel):
    id: str
    source: str
    source_id: str | None
    title: str
    description: str | None
    status: str
    acceptance_criteria: list[dict]
    body: dict

    class Config:
        from_attributes = True


@router.post("/import", response_model=TicketResponse)
async def import_ticket(req: ImportTicketRequest, db: AsyncSession = Depends(get_db)):
    adapter = ADAPTERS.get(req.source)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {req.source}")

    normalized = adapter.normalize(req.raw)
    criteria = await extract_criteria(normalized.title, normalized.description)

    ticket = Ticket(
        id=str(uuid.uuid4()),
        workspace_id=req.workspace_id,
        source=normalized.source,
        source_id=normalized.source_id,
        title=normalized.title,
        description=normalized.description,
        status=normalized.status,
        body=normalized.body,
        acceptance_criteria=criteria,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post("/", response_model=TicketResponse)
async def create_ticket(req: CreateTicketRequest, db: AsyncSession = Depends(get_db)):
    criteria = [
        {"id": str(uuid.uuid4()), "text": c, "done": False}
        for c in req.acceptance_criteria
    ]
    if not criteria and req.description:
        criteria = await extract_criteria(req.title, req.description)

    ticket = Ticket(
        id=str(uuid.uuid4()),
        workspace_id=req.workspace_id,
        source="custom",
        source_id=None,
        title=req.title,
        description=req.description,
        status="open",
        body={},
        acceptance_criteria=criteria,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/")
async def list_tickets(workspace_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ticket).where(Ticket.workspace_id == workspace_id)
    )
    return result.scalars().all()
