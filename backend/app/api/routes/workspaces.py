import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_or_404
from app.models.workspace import Workspace

router = APIRouter()


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., description="Human-readable workspace name.", examples=["backend-team"])
    repo_path: str = Field(..., description="Absolute path to a git repository on the server's filesystem. Validated to be an existing git repo.", examples=["/home/user/projects/backend"])

    @field_validator("name", "repo_path")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    repo_path: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = Field(None, description="New workspace name. Omit to leave unchanged.", examples=["backend-team-v2"])
    repo_path: str | None = Field(None, description="New repo path. Validated to be an existing git repo. Omit to leave unchanged.", examples=["/home/user/projects/backend-v2"])


def _validate_git_repo(repo_path: str) -> Path:
    path = Path(repo_path).resolve()
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {repo_path}")
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(path),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Not a git repository: {repo_path}")
    return path


@router.post(
    "",
    response_model=WorkspaceResponse,
    summary="Create a workspace",
    description="Create a workspace linked to a git repository path on the server. Returns 400 if the path does not exist or is not a git repository.",
)
async def create_workspace(
    req: CreateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
):
    resolved = _validate_git_repo(req.repo_path)
    workspace = Workspace(
        id=str(uuid.uuid4()),
        name=req.name,
        repo_path=str(resolved),
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.get(
    "",
    response_model=list[WorkspaceResponse],
    summary="List workspaces",
    description="Return all workspaces ordered by creation time.",
)
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace).order_by(Workspace.created_at))
    return result.scalars().all()


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get a workspace",
    description="Retrieve a single workspace by ID. Returns 404 if not found.",
)
async def get_workspace(workspace_id: str, db: AsyncSession = Depends(get_db)):
    return await get_or_404(db, Workspace, workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update a workspace",
    description="Update `name` and/or `repo_path`. Omit any field to leave it unchanged. `repo_path` is validated as an existing git repository.",
)
async def update_workspace(
    workspace_id: str,
    req: UpdateWorkspaceRequest,
    db: AsyncSession = Depends(get_db),
):
    workspace = await get_or_404(db, Workspace, workspace_id)
    if req.name is not None:
        if not req.name.strip():
            raise HTTPException(status_code=422, detail="name must not be blank")
        workspace.name = req.name
    if req.repo_path is not None:
        resolved = _validate_git_repo(req.repo_path)
        workspace.repo_path = str(resolved)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete(
    "/{workspace_id}",
    status_code=204,
    summary="Delete a workspace",
    description="Delete a workspace by ID. Returns 204 on success, 404 if not found. Does not cascade-delete agents or tickets.",
)
async def delete_workspace(workspace_id: str, db: AsyncSession = Depends(get_db)):
    workspace = await get_or_404(db, Workspace, workspace_id)
    await db.delete(workspace)
    await db.commit()
