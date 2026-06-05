from typing import Any

from app.services.adapters.base import NormalizedTicket, TicketAdapter

_STATUS_MAP = {
    "Todo": "open",
    "In Progress": "in_progress",
    "Done": "done",
    "Cancelled": "done",
    "Backlog": "open",
}


class LinearAdapter(TicketAdapter):
    def normalize(self, raw: dict[str, Any]) -> NormalizedTicket:
        return NormalizedTicket(
            source="linear",
            source_id=raw["identifier"],
            title=raw.get("title", ""),
            description=raw.get("description"),
            status=self.extract_status(raw),
            body=raw,
        )

    def extract_status(self, raw: dict[str, Any]) -> str:
        state_name = raw.get("state", {}).get("name", "")
        return _STATUS_MAP.get(state_name, "open")
