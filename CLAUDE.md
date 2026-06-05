# Treco — Codebase Reference

## What It Is

Open source agent observability platform. Agents report progress on tickets in real time.
Tracks acceptance criteria, token consumption, and per-ticket cost across any ticket source
(Jira, Linear, Asana, GitHub Issues, or custom).

## Code Standards — NON-NEGOTIABLE

**Write clean, correct, testable, and safe code. Every time. No exceptions.**

### Clean
- No dead code. No commented-out blocks. No TODOs left in PRs.
- Functions do one thing. Names are self-documenting.
- No abstractions that don't earn their complexity.
- Three similar lines beats a premature helper.

### Correct
- Handle errors at boundaries. Trust internal invariants.
- No silent failures. Raise or return — never swallow.
- Validate all external input (HTTP bodies, ticket payloads, SDK calls).
- Type everything. No `any` in TypeScript. No untyped Python.

### Testable
- Every service has unit tests. Every adapter has integration tests.
- No test mocks that diverge from real behavior (no fake DB unless clearly marked).
- Tests live next to the code they test or in `tests/` mirroring the source tree.
- Test names describe behavior: `test_jira_adapter_normalizes_missing_description`.

### Safe
- No SQL injection — use parameterized queries always.
- No XSS — sanitize all ticket body content before rendering.
- API keys and tokens never logged, never in error messages.
- Agent SDK keys are scoped per workspace — no cross-tenant leakage.
- OWASP Top 10 is the floor, not the ceiling.

### Comments
- Default: no comments. Well-named code explains itself.
- Write a comment only when the WHY is non-obvious: a workaround, a hidden constraint, a subtle invariant.
- Never explain WHAT the code does. Never reference ticket numbers or callers.

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python), PostgreSQL + JSONB |
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind |
| Agent SDK | Python (primary), TypeScript (secondary) |
| Queue | `agent_events` table + polling worker |
| Auth | JWT (self-hosted) |
| Storage | SQLite (dev/local) or Postgres (team/prod) |

## Repo Layout

```
backend/
  app/
    main.py               # FastAPI app factory
    api/router.py         # Route mounting
    core/
      config.py           # Pydantic Settings — all env vars here
      database.py         # DB session + engine
    models/               # SQLAlchemy models
      ticket.py           # Unified ticket (JSONB body)
      agent.py            # Agent identity + status
      event.py            # agent_events stream
    services/
      adapters/           # One file per ticket source
        base.py           # TicketAdapter ABC
        jira.py
        linear.py
        asana.py
        github.py
      ticket_normalizer/  # Normalize raw payload → unified schema
      criteria_extractor/ # LLM-based acceptance criteria extraction
    worker/
      runner.py           # Event processor
      main.py             # Worker entry point
  sdk/python/             # Agent SDK (published to PyPI)
  migrations/             # Raw SQL migrations (numbered)
  tests/

frontend/
  app/                    # Next.js App Router
    dashboard/            # Agent board + overview
    tickets/              # Ticket list + detail
    agents/               # Per-agent view
  components/             # Reusable UI
  lib/api.ts              # All backend calls

docs/
  architecture.md
  sdk.md
```

## Key Invariants

- Ticket `body` field is always raw provider JSON. Never mutate it.
- Normalized fields (`title`, `acceptance_criteria`) are always derived — never hand-edited.
- Agent events are append-only. No updates, no deletes.
- Cost is always computed at read time from stored token counts — never stored as a derived value.
