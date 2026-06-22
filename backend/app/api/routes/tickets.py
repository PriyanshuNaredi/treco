import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_or_404
from app.models.ticket import Ticket
from app.models.workspace import Workspace
from app.services import agent_runner
from app.services.adapters import ADAPTERS
from app.services.adapters.base import NormalizedTicket
from app.services.criteria_extractor import create_criterion, extract_criteria

router = APIRouter()


class _WorkspaceIdModel(BaseModel):
    workspace_id: str

    @field_validator("workspace_id")
    @classmethod
    def validate_workspace_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("workspace_id is required")
        return v


class ImportTicketRequest(_WorkspaceIdModel):
    source: Literal["jira", "linear", "asana", "github"] = Field(
        ..., description="Ticket source system.", examples=["github"]
    )
    raw: dict[str, Any] = Field(
        ..., description="Raw provider API response body. Passed unchanged to the source adapter."
    )


class CreateTicketRequest(BaseModel):
    workspace_id: str | None = Field(None, description="Workspace to assign this ticket to.", examples=["ws-abc123"])
    title: str = Field(..., description="Short title for the ticket.", examples=["Fix login redirect loop"])
    description: str | None = Field(None, description="Longer description. Used for LLM criteria extraction if no explicit criteria are provided.")
    acceptance_criteria: list[str] = Field(
        default=[],
        description="Explicit list of acceptance criteria strings. If omitted and description is set, criteria are extracted by LLM.",
        examples=[["User is redirected to /dashboard after login", "Token is stored in localStorage"]],
    )


class FetchGitHubIssueRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace to assign the fetched ticket to.", examples=["ws-abc123"])
    repo: str = Field(..., description="GitHub repo in `owner/name` format.", examples=["acme/backend"])
    issue_number: int = Field(..., description="GitHub issue number.", examples=[42])
    token: str = Field(..., description="GitHub personal access token with `repo` or `public_repo` scope.")


class FetchLinearIssueRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace to assign the fetched ticket to.", examples=["ws-abc123"])
    issue_id: str = Field(..., description="Linear issue ID (e.g. `ENG-123`).", examples=["ENG-123"])
    api_key: str = Field(..., description="Linear personal API key.")


class FetchAsanaTaskRequest(BaseModel):
    workspace_id: str = Field(..., description="Workspace to assign the fetched ticket to.", examples=["ws-abc123"])
    task_gid: str = Field(..., description="Asana task GID.", examples=["1234567890123456"])
    token: str = Field(..., description="Asana personal access token.")


class BulkImportRequest(_WorkspaceIdModel):
    source: Literal["github", "linear", "asana"] = Field(
        ..., description="Source system to bulk-import from.", examples=["github"]
    )
    token: str = Field(..., description="API token for the source system.")
    repo: str | None = Field(None, description="GitHub repo (`owner/name`). Required when source is `github`.", examples=["acme/backend"])
    team_key: str | None = Field(None, description="Linear team key (1–20 uppercase alphanumeric). Required when source is `linear`.", examples=["ENG"])
    project_gid: str | None = Field(None, description="Asana project GID. Required when source is `asana`.", examples=["1234567890123456"])
    limit: int = Field(20, description="Max tickets to import (capped at 200).", examples=[20])

    @field_validator("team_key")
    @classmethod
    def validate_team_key(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[A-Z0-9_-]{1,20}", v):
            raise ValueError("team_key must be 1–20 uppercase alphanumeric characters")
        return v


class FetchUrlRequest(_WorkspaceIdModel):
    url: str = Field(..., description="Full URL of the ticket. Currently supports public GitHub issue URLs only.", examples=["https://github.com/acme/backend/issues/42"])


class TicketResponse(BaseModel):
    id: str
    workspace_id: str | None
    source: str
    source_id: str | None
    title: str
    description: str | None
    status: str
    acceptance_criteria: list[dict]
    body: dict

    model_config = ConfigDict(from_attributes=True)


class ImplementTicketRequest(BaseModel):
    prompt: str = Field(..., description="System prompt / instructions passed to the agent that will work this ticket.", examples=["You are a senior engineer. Follow the acceptance criteria exactly."])
    agent_name: str | None = Field(None, description="Name for the spawned agent. Auto-generated from ticket title if omitted.", examples=["agent-fix-login"])

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt is required")
        return v


class ImplementTicketResponse(BaseModel):
    agent_id: str
    agent_name: str

    model_config = ConfigDict(from_attributes=True)


class AssignTicketWorkspaceRequest(BaseModel):
    workspace_id: str | None = None


_GITHUB_ISSUE_RE = re.compile(
    r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/(\d+)"
)


async def _upsert_ticket(db: AsyncSession, workspace_id: str, norm: NormalizedTicket) -> Ticket:
    result = await db.execute(
        select(Ticket).where(
            Ticket.workspace_id == workspace_id,
            Ticket.source == norm.source,
            Ticket.source_id == norm.source_id,
        )
    )
    existing = result.scalars().first()
    if existing:
        existing.title = norm.title
        existing.description = norm.description
        existing.status = norm.status
        existing.body = norm.body
        await db.commit()
        await db.refresh(existing)
        return existing

    criteria = await extract_criteria(norm.title, norm.description)
    ticket = Ticket(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        source=norm.source,
        source_id=norm.source_id,
        title=norm.title,
        description=norm.description,
        status=norm.status,
        body=norm.body,
        acceptance_criteria=criteria,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.post(
    "/import",
    response_model=TicketResponse,
    summary="Import ticket from raw provider payload",
    description="Normalize a raw provider API response (Jira, Linear, Asana, or GitHub) and upsert it as a ticket. Re-posting the same `source`+`source_id` pair updates the existing record.",
)
async def import_ticket(req: ImportTicketRequest, db: AsyncSession = Depends(get_db)):
    adapter = ADAPTERS.get(req.source)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {req.source}")
    normalized = adapter.normalize(req.raw)
    return await _upsert_ticket(db, req.workspace_id, normalized)


@router.post(
    "/fetch/github",
    response_model=TicketResponse,
    summary="Fetch and import a GitHub issue",
    description="Fetch a single GitHub issue by repo and issue number, normalize it, and upsert it as a ticket. Requires a GitHub token with `repo` or `public_repo` scope.",
)
async def fetch_github_issue(req: FetchGitHubIssueRequest, db: AsyncSession = Depends(get_db)):
    adapter = ADAPTERS["github"]
    normalized = await adapter.fetch_issue(req.repo, req.issue_number, req.token)
    return await _upsert_ticket(db, req.workspace_id, normalized)


@router.post(
    "/fetch/linear",
    response_model=TicketResponse,
    summary="Fetch and import a Linear issue",
    description="Fetch a Linear issue by ID, normalize it, and upsert it as a ticket.",
)
async def fetch_linear_issue(req: FetchLinearIssueRequest, db: AsyncSession = Depends(get_db)):
    adapter = ADAPTERS["linear"]
    normalized = await adapter.fetch_issue(req.issue_id, req.api_key)
    return await _upsert_ticket(db, req.workspace_id, normalized)


@router.post(
    "/fetch/asana",
    response_model=TicketResponse,
    summary="Fetch and import an Asana task",
    description="Fetch an Asana task by GID, normalize it, and upsert it as a ticket.",
)
async def fetch_asana_task(req: FetchAsanaTaskRequest, db: AsyncSession = Depends(get_db)):
    adapter = ADAPTERS["asana"]
    normalized = await adapter.fetch_task(req.task_gid, req.token)
    return await _upsert_ticket(db, req.workspace_id, normalized)


@router.post(
    "/fetch/bulk",
    response_model=list[TicketResponse],
    summary="Bulk import tickets from a source",
    description="Fetch multiple open tickets from GitHub, Linear, or Asana and upsert each one. Existing tickets (matched by `source`+`source_id`) are updated in place.",
)
async def bulk_import(req: BulkImportRequest, db: AsyncSession = Depends(get_db)):
    if req.source == "github":
        if not req.repo:
            raise HTTPException(status_code=400, detail="repo is required for GitHub bulk import")
        adapter = ADAPTERS["github"]
        normalized_list = await adapter.fetch_issues(req.repo, req.token, req.limit)
    elif req.source == "asana":
        if not req.project_gid:
            raise HTTPException(status_code=400, detail="project_gid is required for Asana bulk import")
        adapter = ADAPTERS["asana"]
        normalized_list = await adapter.fetch_tasks_by_project(req.project_gid, req.token, req.limit)
    else:
        adapter = ADAPTERS["linear"]
        normalized_list = await adapter.fetch_issues(req.team_key, req.token, req.limit)
    return [await _upsert_ticket(db, req.workspace_id, n) for n in normalized_list]


@router.post(
    "/fetch/url",
    response_model=TicketResponse,
    summary="Fetch ticket from a URL",
    description="Detect the source from the URL and fetch + upsert the ticket. Currently supports public GitHub issue URLs (`https://github.com/{owner}/{repo}/issues/{number}`).",
)
async def fetch_url(req: FetchUrlRequest, db: AsyncSession = Depends(get_db)):
    m = _GITHUB_ISSUE_RE.match(req.url.strip())
    if m:
        owner, repo, issue_number = m.groups()
        adapter = ADAPTERS["github"]
        normalized = await adapter.fetch_issue(f"{owner}/{repo}", int(issue_number))
        return await _upsert_ticket(db, req.workspace_id, normalized)
    raise HTTPException(
        status_code=400,
        detail="Unsupported URL. Only public GitHub issue URLs are supported.",
    )


@router.post(
    "",
    response_model=TicketResponse,
    summary="Create a custom ticket",
    description="Create a ticket with an explicit title, description, and optional acceptance criteria. If `acceptance_criteria` is omitted and `description` is provided, criteria are extracted by LLM.",
)
async def create_ticket(req: CreateTicketRequest, db: AsyncSession = Depends(get_db)):
    criteria = [create_criterion(c) for c in req.acceptance_criteria]
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


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get a ticket",
    description="Retrieve a single ticket by ID. Returns 404 if not found.",
)
async def get_ticket(ticket_id: str, db: AsyncSession = Depends(get_db)):
    return await get_or_404(db, Ticket, ticket_id)


@router.post(
    "/{ticket_id}/implement",
    response_model=ImplementTicketResponse,
    summary="Spawn an agent to implement a ticket",
    description=(
        "Mint a new agent, assign it to this ticket, and spawn a background `claude` process "
        "that will work through the acceptance criteria. The agent's API key is returned once — "
        "the spawned process uses it to post events. Requires the ticket to belong to a workspace "
        "with a `repo_path` configured."
    ),
)
async def implement_ticket(
    ticket_id: str,
    req: ImplementTicketRequest,
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_or_404(db, Ticket, ticket_id)
    if not ticket.workspace_id:
        raise HTTPException(status_code=400, detail="Assign this ticket to a workspace first")
    workspace = await get_or_404(db, Workspace, ticket.workspace_id)
    if not workspace.repo_path:
        raise HTTPException(status_code=400, detail="Workspace has no repo path configured")
    agent_name = req.agent_name or f"agent-{ticket.title[:24]}"
    agent, raw_key = await agent_runner.mint_agent(
        workspace_id=ticket.workspace_id,
        name=agent_name,
        db=db,
    )
    await agent_runner.spawn_agent_run(agent, raw_key, ticket, req.prompt, workspace.repo_path, db)
    return ImplementTicketResponse(agent_id=agent.id, agent_name=agent.name)


@router.patch(
    "/{ticket_id}/workspace",
    response_model=TicketResponse,
    summary="Assign or unassign a ticket's workspace",
    description="Set or clear the `workspace_id` on a ticket. Pass `null` to unassign. Returns 404 if the workspace does not exist.",
)
async def assign_ticket_workspace(
    ticket_id: str,
    req: AssignTicketWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
):
    ticket = await get_or_404(db, Ticket, ticket_id)
    if req.workspace_id is not None:
        await get_or_404(db, Workspace, req.workspace_id)
    ticket.workspace_id = req.workspace_id
    await db.commit()
    await db.refresh(ticket)
    return ticket


@router.get(
    "",
    response_model=list[TicketResponse],
    summary="List tickets",
    description="Return tickets ordered by creation time (newest first). Optionally filter by `workspace_id`. `limit` is capped at 200.",
)
async def list_tickets(
    workspace_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Ticket)
    if workspace_id is not None:
        query = query.where(Ticket.workspace_id == workspace_id)
    query = query.order_by(Ticket.created_at.desc()).limit(min(limit, 200)).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()
