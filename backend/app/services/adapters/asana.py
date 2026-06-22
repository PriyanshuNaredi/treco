from typing import Any

import httpx
from fastapi import HTTPException

from app.services.adapters.base import NormalizedTicket, TicketAdapter

_ASANA_API = "https://app.asana.com/api/1.0"
_TASK_OPT_FIELDS = "gid,name,notes,completed"


class AsanaAdapter(TicketAdapter):
    def normalize(self, raw: dict[str, Any]) -> NormalizedTicket:
        return NormalizedTicket(
            source="asana",
            source_id=str(raw["gid"]),
            title=raw.get("name", ""),
            description=raw.get("notes") or None,
            status=self.extract_status(raw),
            body=raw,
        )

    def extract_status(self, raw: dict[str, Any]) -> str:
        return "done" if raw.get("completed") else "open"

    async def fetch_task(self, task_gid: str, token: str) -> NormalizedTicket:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{_ASANA_API}/tasks/{task_gid}",
                params={"opt_fields": _TASK_OPT_FIELDS},
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="Task not found")
            r.raise_for_status()
        return self.normalize(r.json()["data"])

    async def fetch_tasks_by_project(
        self, project_gid: str, token: str, limit: int = 20
    ) -> list[NormalizedTicket]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{_ASANA_API}/projects/{project_gid}/tasks",
                params={"opt_fields": _TASK_OPT_FIELDS, "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            r.raise_for_status()
        tasks = r.json().get("data", [])
        return [self.normalize(t) for t in tasks]
