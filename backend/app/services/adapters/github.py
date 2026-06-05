from typing import Any

from app.services.adapters.base import NormalizedTicket, TicketAdapter


class GitHubIssueAdapter(TicketAdapter):
    def normalize(self, raw: dict[str, Any]) -> NormalizedTicket:
        return NormalizedTicket(
            source="github",
            source_id=str(raw["number"]),
            title=raw.get("title", ""),
            description=raw.get("body"),
            status=self.extract_status(raw),
            body=raw,
        )

    def extract_status(self, raw: dict[str, Any]) -> str:
        return "done" if raw.get("state") == "closed" else "open"
