from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class NormalizedTicket(BaseModel):
    source: str
    source_id: str
    title: str
    description: str | None
    status: str
    body: dict[str, Any]  # raw provider payload, preserved as-is


class TicketAdapter(ABC):
    """Normalize a provider ticket payload into a unified schema."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> NormalizedTicket:
        ...

    @abstractmethod
    def extract_status(self, raw: dict[str, Any]) -> str:
        ...
