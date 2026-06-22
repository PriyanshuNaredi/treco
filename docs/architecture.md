# Architecture

## System Diagram

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Agent Process (your Claude Code session, script, or custom agent)   │
  │                                                                      │
  │   ┌─────────────┐    ┌──────────────────────────────────────────┐   │
  │   │  treco CLI  │    │  TrecoClient (Python SDK)                │   │
  │   │             │    │  client.start() / check() / done() / log │   │
  │   │  treco start│    │  POST /api/events  (X-Agent-Key header)  │   │
  │   │  treco check│    └──────────────────┬───────────────────────┘   │
  │   │  treco done │                       │                           │
  │   └──────┬──────┘                       │                           │
  │          │ httpx                        │ httpx                     │
  └──────────┼──────────────────────────────┼───────────────────────────┘
             │                              │
             ▼                              ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │  FastAPI Backend  (port 8001)                                        │
  │                                                                      │
  │  POST /api/init          ← one-shot bootstrap (workspace + agent)    │
  │  POST /api/tickets       ← create / import ticket                    │
  │  GET  /api/tickets       ← list tickets                              │
  │  POST /api/events        ← append event (X-Agent-Key auth)          │
  │  GET  /api/events/stream ← SSE stream → dashboard                   │
  │  GET  /api/events/cost   ← token cost aggregation                   │
  │  POST /api/agents        ← register agent                           │
  │                                                                      │
  │  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
  │  │  tickets.py    │  │  events.py        │  │  agents.py          │  │
  │  │  CRUD + import │  │  append + cost    │  │  create + resolve   │  │
  │  └───────┬────────┘  └────────┬──────────┘  └──────────┬──────────┘  │
  │          │                    │                         │            │
  │  ┌───────▼────────────────────▼─────────────────────────▼──────────┐ │
  │  │  SQLAlchemy Async ORM                                            │ │
  │  └───────────────────────────────────┬──────────────────────────────┘ │
  │                                      │                              │
  │  ┌───────────────────────────────────▼──────────────────────────────┐ │
  │  │  criteria_extractor  (LLM: claude-haiku / gpt-4o-mini)          │ │
  │  │  called once on ticket import — never on reads                  │ │
  │  └──────────────────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────────────────┘
             │  SQLAlchemy async                │  SSE
             ▼                                 ▼
  ┌──────────────────────┐         ┌───────────────────────────────────┐
  │  Database            │         │  Next.js Dashboard (port 3000)    │
  │                      │         │                                   │
  │  PostgreSQL (prod)   │         │  lib/api.ts  → fetch()            │
  │  SQLite (dev/test)   │         │  real-time event feed via SSE     │
  │                      │         │  JWT auth (browser sessions)      │
  └──────────────────────┘         └───────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │  Ticket Sources (external)                                           │
  │                                                                      │
  │  GitHub Issues ──┐                                                   │
  │  Linear ─────────┼──► TicketAdapter → NormalizedTicket → DB         │
  │  Jira ───────────┘    (body stored raw; fields derived by LLM)      │
  │  Custom / manual                                                     │
  └──────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Bootstrap (`treco init`)

```
CLI
 └─ POST /api/init
     ├─ creates Workspace (workspace_id)
     ├─ creates Agent (returns raw api_key — shown once, never again)
     └─ writes ~/.treco/config.json  (chmod 600)
```

### 2. Start a ticket session (`treco start <ticket-id>`)

```
CLI
 └─ POST /api/events  { event_type: "ticket_started", ticket_id }
     ├─ _resolve_agent(X-Agent-Key)  →  SHA-256 hash lookup
     ├─ inserts AgentEvent row (append-only)
     ├─ sets Agent.status = "working", Agent.current_ticket_id
     └─ broadcasts over SSE stream
```

### 3. Progress events (`treco check`, `treco log`, SDK methods)

```
Agent / CLI
 └─ POST /api/events  { event_type: "criterion_checked" | "log" | "heartbeat" | … }
     ├─ authenticates via X-Agent-Key
     ├─ appends AgentEvent (tokens_in, tokens_out, payload)
     ├─ if criterion_checked: marks that criterion done in Ticket.acceptance_criteria
     └─ broadcasts SSE
```

### 4. Done (`treco done`)

```
CLI
 └─ POST /api/events  { event_type: "done" }
     ├─ sets Agent.status = "idle", clears current_ticket_id
     ├─ sets Ticket.status = "done"
     └─ clears ~/.treco_session
```

### 5. Dashboard reads

```
Browser (JWT session)
 ├─ GET /api/tickets          ← list tickets for workspace
 ├─ GET /api/events?ticket_id ← full event history
 ├─ GET /api/events/cost      ← SUM(tokens_in/out) computed in SQL
 └─ GET /api/events/stream    ← SSE for live updates
```

## Data Model

### Ticket

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | primary key |
| `workspace_id` | string | tenant boundary — every query filters on this |
| `source` | string | `jira` \| `linear` \| `asana` \| `github` \| `custom` |
| `source_id` | string? | provider's native ID |
| `title` | text | derived from `body` via adapter; never hand-set |
| `description` | text? | derived from `body` |
| `status` | string | `open` → `done` |
| `body` | JSONB | raw provider payload — immutable after import |
| `acceptance_criteria` | JSONB | `[{id, text, done}]` — LLM-extracted on import |
| `created_at` / `updated_at` | datetime | |

`body` is the source of truth. `title`, `description`, and `acceptance_criteria` are derived once at import time by the criteria extractor. They are never re-derived on reads and never overwritten by arbitrary input.

### Agent

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | primary key |
| `workspace_id` | string | |
| `name` | string | |
| `api_key_hash` | string | SHA-256 of raw key; raw key returned once, never stored |
| `status` | string | `idle` \| `working` \| `awaiting_approval` \| `error` |
| `current_ticket_id` | string? | set when `status = working` |
| `pid` | int? | subprocess PID while working |
| `last_seen_at` | datetime? | updated on heartbeat; agent marked offline after 5 min silence |

### AgentEvent

Append-only. No `UPDATE`, no `DELETE`, ever.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | primary key |
| `agent_id` | string | indexed |
| `ticket_id` | string | indexed |
| `workspace_id` | string | indexed — all queries filter here |
| `event_type` | string | see types below |
| `criterion_id` | string? | for `criterion_checked` / `criterion_failed` |
| `tokens_in` | int | LLM input tokens consumed during this event |
| `tokens_out` | int | LLM output tokens |
| `model` | string? | model identifier |
| `payload` | JSONB | free-form: log message, PR URL, error details, etc. |
| `created_at` | datetime | indexed |

**Event types:**

| Type | Meaning |
|------|---------|
| `ticket_started` | agent begins work on a ticket |
| `criterion_checked` | acceptance criterion marked done |
| `criterion_failed` | criterion explicitly failed |
| `pr_opened` | pull request URL recorded |
| `done` | agent finished the ticket |
| `error` | agent encountered an error |
| `log` | free-form log message |
| `heartbeat` | liveness ping — keeps `last_seen_at` current |
| `deviation` | agent deviated from expected path |

## Design Decisions

### Why append-only events?

`agent_events` is a ledger, not state. Mutating past events would hide what actually happened — the entire point of an observability platform is an accurate audit trail. Cost is derived from `SUM(tokens_in/out)` across events at read time rather than persisted, so it always reflects reality.

### Why is `Ticket.body` immutable?

The raw provider payload is the canonical record of what the provider said. Normalizing (extracting `title`, `description`, criteria) is a one-way transformation applied once at import. If normalization were re-applied on every read, a provider API change could silently corrupt existing data. Storing raw `body` and deriving on import gives reproducibility: you can always re-import from `body` without hitting the provider again.

### Why two auth schemes?

CLI/SDK agents use `X-Agent-Key` (SHA-256 hashed, no expiry). This is a long-lived machine credential that fits how agents work — no browser, no session cookie, no token refresh. Dashboard users use JWT (short-lived, scoped to a workspace session). Mixing these on the same route would require both contexts to be satisfied simultaneously, breaking either the agent workflow or the browser session model.

### Why SQLite in dev, Postgres in prod?

`AnyJSON` (`JSONB` with `.with_variant(JSON(), "sqlite")`) lets ticket `body` and event `payload` store structured data on both engines. SQLite removes the Postgres dependency for local dev and CI, while Postgres gives JSONB indexing and production query performance. The ORM layer is identical — the only difference is the DB URL and `DATABASE_MODE` env var.

### Why LLM criteria extraction only on import?

Extraction uses `claude-haiku` (fast, cheap) and is fallible — network failures, JSON parse errors, model refusals. Calling it at import and persisting the result means: reads are instant, a downstream LLM outage doesn't affect in-flight agent sessions, and the fallback (`_parse_checkboxes`) can run synchronously without blocking ticket creation.

### Workspace isolation as the only tenant boundary

Every model has `workspace_id`. Every query `.where(Model.workspace_id == workspace_id)`. There is no role hierarchy below workspace — an agent key scoped to a workspace can read/write any ticket or event in that workspace, and nothing outside it. This keeps authorization simple enough to audit at a glance.
