import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

import httpx


class TrecoClient:
    """Minimal SDK for agents to report progress to Treco."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self._api_key = api_key or os.environ["TRECO_API_KEY"]
        self._base_url = (base_url or os.environ.get("TRECO_URL", "http://localhost:8001")).rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Agent-Key": self._api_key},
            timeout=10.0,
        )

    async def heartbeat(self, ticket_id: str) -> None:
        """Send a keepalive ping — updates agent `last_seen_at` on the server."""
        await self._emit(ticket_id, "heartbeat")

    async def start(self, ticket_id: str) -> None:
        """Signal that work on *ticket_id* has begun; sets ticket status to `in_progress`."""
        await self._emit(ticket_id, "ticket_started")

    async def check(
        self,
        ticket_id: str,
        criterion_id: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str | None = None,
    ) -> None:
        """Mark an acceptance criterion as satisfied.

        Args:
            ticket_id: Ticket the criterion belongs to.
            criterion_id: ID of the criterion to mark done.
            tokens_in: Input tokens consumed in the LLM call that completed it.
            tokens_out: Output tokens generated.
            model: Model used (e.g. ``"claude-haiku-4-5-20251001"``).
        """
        await self._emit(
            ticket_id,
            "criterion_checked",
            criterion_id=criterion_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
        )

    async def fail_criterion(self, ticket_id: str, criterion_id: str, reason: str = "") -> None:
        """Record that a criterion could not be satisfied.

        Args:
            ticket_id: Ticket the criterion belongs to.
            criterion_id: ID of the criterion that failed.
            reason: Human-readable explanation stored in the event payload.
        """
        await self._emit(ticket_id, "criterion_failed", criterion_id=criterion_id, payload={"reason": reason})

    async def log(self, ticket_id: str, message: str, payload: dict[str, Any] | None = None) -> None:
        """Emit a free-form log message visible in the ticket event stream.

        Args:
            ticket_id: Ticket this log line belongs to.
            message: Log text.
            payload: Optional extra fields merged into the event payload.
        """
        await self._emit(ticket_id, "log", payload={"message": message, **(payload or {})})

    async def pr_opened(
        self,
        ticket_id: str,
        url: str,
        pr_number: int | None = None,
    ) -> None:
        """Record that the agent opened a pull request for this ticket.

        Args:
            ticket_id: Ticket the PR addresses.
            url: Full URL of the opened PR.
            pr_number: Numeric PR identifier, if known.
        """
        p: dict[str, Any] = {"url": url}
        if pr_number is not None:
            p["pr_number"] = pr_number
        await self._emit(ticket_id, "pr_opened", payload=p)

    async def done(self, ticket_id: str, tokens_in: int = 0, tokens_out: int = 0) -> None:
        """Signal successful completion; sets ticket status to `done`.

        Args:
            ticket_id: Ticket that was completed.
            tokens_in: Total input tokens for the final LLM call (optional).
            tokens_out: Total output tokens for the final LLM call (optional).
        """
        await self._emit(ticket_id, "done", tokens_in=tokens_in, tokens_out=tokens_out)

    async def error(self, ticket_id: str, message: str) -> None:
        """Signal an unrecoverable error; sets agent status to `error`.

        Args:
            ticket_id: Ticket the agent was working on.
            message: Error description stored in the event payload.
        """
        await self._emit(ticket_id, "error", payload={"message": message})

    async def _emit(
        self,
        ticket_id: str,
        event_type: str,
        criterion_id: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        model: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        body = {
            "ticket_id": ticket_id,
            "event_type": event_type,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "payload": payload or {},
        }
        if criterion_id:
            body["criterion_id"] = criterion_id
        if model:
            body["model"] = model

        response = await self._http.post("/api/events/", json=body)
        response.raise_for_status()

    async def _heartbeat_loop(self, ticket_id: str) -> None:
        while True:
            await asyncio.sleep(60)
            try:
                await self.heartbeat(ticket_id)
            except Exception:
                pass

    @asynccontextmanager
    async def track(self, ticket_id: str):
        """Context manager that wraps agent work with automatic lifecycle events.

        Emits ``ticket_started`` on entry, ``done`` on clean exit, and ``error``
        if an exception propagates. Also sends a ``heartbeat`` every 60 s for the
        duration. The exception is re-raised after the error event is emitted.

        Example::

            async with client.track("ticket-abc") as c:
                await c.log("ticket-abc", "starting work")
                await c.check("ticket-abc", criterion_id="crit-1")
        """
        await self.start(ticket_id)
        hb_task = asyncio.create_task(self._heartbeat_loop(ticket_id))
        try:
            yield self
            await self.done(ticket_id)
        except Exception as exc:
            await self.error(ticket_id, str(exc))
            raise
        finally:
            hb_task.cancel()

    async def close(self) -> None:
        await self._http.aclose()
