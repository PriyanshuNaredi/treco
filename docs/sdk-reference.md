# SDK Reference — TrecoClient

Python SDK for agents to report progress to Treco in real time.

**Package:** `treco` · **PyPI:** `pip install treco` · **Requires:** Python 3.10+

---

## Installation

```bash
pip install treco
```

For agents that also run the Treco backend locally:

```bash
pip install "treco[server]"
```

---

## Configuration

`TrecoClient` reads credentials from constructor arguments or environment variables.

| Source | Variable | Description |
|--------|----------|-------------|
| Env var | `TRECO_API_KEY` | Agent API key (required if not passed to constructor) |
| Env var | `TRECO_URL` | Backend base URL (default: `http://localhost:8001`) |
| Config file | `~/.treco/config.json` | Written by `treco init`; CLI reads this automatically |

The config file is chmod 600. Never commit it or log its contents.

---

## TrecoClient

```python
class TrecoClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None: ...
```

Creates an async HTTP client bound to one agent identity. Reuses a single `httpx.AsyncClient` for the client's lifetime — do not create a new instance per request.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `$TRECO_API_KEY` | Agent API key. Raises `KeyError` if absent and env var not set. |
| `base_url` | `str \| None` | `$TRECO_URL` or `http://localhost:8001` | Treco backend URL. Trailing slash stripped automatically. |

**Example**

```python
from treco import TrecoClient

# From environment variables
client = TrecoClient()

# Explicit
client = TrecoClient(api_key="sk-...", base_url="https://treco.example.com")
```

---

## Methods

All methods are async and raise `httpx.HTTPStatusError` on non-2xx responses.

---

### `start`

```python
async def start(self, ticket_id: str) -> None
```

Emits `ticket_started`. Sets agent status to `working` and binds the agent to this ticket. Call once when the agent begins work.

```python
await client.start("ticket-uuid-here")
```

---

### `heartbeat`

```python
async def heartbeat(self, ticket_id: str) -> None
```

Emits `heartbeat`. Signals the agent is alive without changing status. The `track` context manager calls this automatically every 60 seconds.

```python
await client.heartbeat(ticket_id)
```

---

### `check`

```python
async def check(
    self,
    ticket_id: str,
    criterion_id: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    model: str | None = None,
) -> None
```

Emits `criterion_checked`. Marks an acceptance criterion done and records token usage for cost tracking. The criterion's `done` flag is set to `True` in the database.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticket_id` | `str` | Ticket UUID |
| `criterion_id` | `str` | Criterion UUID from `ticket.acceptance_criteria[n].id` |
| `tokens_in` | `int` | Input tokens consumed completing this criterion |
| `tokens_out` | `int` | Output tokens consumed completing this criterion |
| `model` | `str \| None` | Model name, e.g. `"claude-sonnet-4-6"` |

```python
await client.check(
    ticket_id,
    criterion_id="3f1ab0a1-318c-423f-88a7-a7c88703f93a",
    tokens_in=1200,
    tokens_out=340,
    model="claude-sonnet-4-6",
)
```

---

### `fail_criterion`

```python
async def fail_criterion(
    self,
    ticket_id: str,
    criterion_id: str,
    reason: str = "",
) -> None
```

Emits `criterion_failed`. Records that the agent attempted but could not satisfy a criterion. Does not change the criterion's `done` flag.

```python
await client.fail_criterion(
    ticket_id,
    criterion_id="3f1ab0a1-318c-423f-88a7-a7c88703f93a",
    reason="Test suite unavailable in sandbox",
)
```

---

### `log`

```python
async def log(
    self,
    ticket_id: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> None
```

Emits `log`. Appends a free-form progress message. `payload` is merged into the event body under `message`.

```python
await client.log(ticket_id, "Running test suite")

# With structured context
await client.log(ticket_id, "File edited", payload={"file": "app/main.py", "lines_changed": 12})
```

---

### `done`

```python
async def done(
    self,
    ticket_id: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> None
```

Emits `done`. Sets agent status to `idle`. Pass cumulative token totals for the session if not already reported per-criterion. The `track` context manager calls this automatically on clean exit.

```python
await client.done(ticket_id, tokens_in=8400, tokens_out=2100)
```

---

### `error`

```python
async def error(self, ticket_id: str, message: str) -> None
```

Emits `error`. Sets agent status to `error`. The `track` context manager calls this automatically on unhandled exception, then re-raises.

```python
await client.error(ticket_id, "Unrecoverable: upstream API returned 503")
```

---

### `track`

```python
@asynccontextmanager
async def track(self, ticket_id: str) -> AsyncIterator[TrecoClient]
```

Async context manager that handles the full session lifecycle:

1. Calls `start` on entry
2. Spawns a background task calling `heartbeat` every 60 seconds
3. Calls `done` on clean exit
4. Calls `error` and re-raises on exception
5. Cancels the heartbeat task in all cases

Yields `self` so you can call other methods without a separate reference.

```python
async def run_agent(ticket_id: str) -> None:
    async with TrecoClient() as client:
        async with client.track(ticket_id) as treco:
            await treco.log(ticket_id, "Starting analysis")

            result = await do_analysis()

            await treco.check(
                ticket_id,
                criterion_id="3f1ab0a1-318c-423f-88a7-a7c88703f93a",
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                model="claude-sonnet-4-6",
            )
```

---

### `close`

```python
async def close(self) -> None
```

Closes the underlying `httpx.AsyncClient`. Call when not using `TrecoClient` as a context manager.

```python
client = TrecoClient()
try:
    await client.start(ticket_id)
    # ...
finally:
    await client.close()
```

---

## Context Manager Usage

`TrecoClient` implements `__aenter__` / `__aexit__` via the underlying `httpx.AsyncClient`, so you can use it as an async context manager:

```python
async with TrecoClient() as client:
    async with client.track(ticket_id) as treco:
        await treco.log(ticket_id, "Working...")
```

Using `async with TrecoClient()` automatically calls `close()` on exit.

---

## Event Types

All events emitted by `TrecoClient` map to these backend event types. The `agent_events` table is append-only — no updates, no deletes.

| Event type | Emitted by | Side effect |
|------------|------------|-------------|
| `ticket_started` | `start()` | Agent status → `working`, `current_ticket_id` set |
| `heartbeat` | `heartbeat()` | Updates `agent.last_seen_at` |
| `criterion_checked` | `check()` | Sets `criterion.done = True` on the ticket |
| `criterion_failed` | `fail_criterion()` | No criterion mutation |
| `log` | `log()` | Triggers deviation detection |
| `done` | `done()` | Agent status → `idle`, `current_ticket_id` cleared |
| `error` | `error()` | Agent status → `error`, `current_ticket_id` cleared |
| `pr_opened` | — | Not emitted by SDK directly; emit via `_emit` if needed |
| `deviation` | Internal | Set by the backend deviation detector, not the agent |

---

## Error Handling

All methods call `response.raise_for_status()`. Wrap calls in try/except when failures should not crash the agent:

```python
try:
    await client.check(ticket_id, criterion_id=cid, tokens_in=800, tokens_out=200)
except httpx.HTTPStatusError as exc:
    # 401: invalid or expired API key
    # 404: ticket not found in this workspace
    print(f"Treco error: {exc.response.status_code}")
```

Network errors raise `httpx.RequestError`. Heartbeat failures inside `track` are silently swallowed so a transient network blip does not abort the agent session.

---

## Full Example

```python
import asyncio
from treco import TrecoClient

TICKET_ID = "b2e3f1a0-..."
CRITERION_REGISTER_APP = "3f1ab0a1-318c-423f-88a7-a7c88703f93a"
CRITERION_ADD_CALLBACK  = "4f0a15d7-f9a5-4f7e-a49e-07d9190c4b5e"

async def main() -> None:
    async with TrecoClient() as client:
        async with client.track(TICKET_ID) as treco:

            await treco.log(TICKET_ID, "Registering OAuth app via GitHub API")
            register_result = await register_github_oauth_app()
            await treco.check(
                TICKET_ID,
                criterion_id=CRITERION_REGISTER_APP,
                tokens_in=register_result.tokens_in,
                tokens_out=register_result.tokens_out,
                model="claude-sonnet-4-6",
            )

            await treco.log(TICKET_ID, "Adding /auth/github/callback endpoint")
            callback_result = await add_callback_endpoint()
            await treco.check(
                TICKET_ID,
                criterion_id=CRITERION_ADD_CALLBACK,
                tokens_in=callback_result.tokens_in,
                tokens_out=callback_result.tokens_out,
                model="claude-sonnet-4-6",
            )

asyncio.run(main())
```

---

## Related

- [CLI Reference](cli-reference.md) — `treco init`, `treco start`, `treco check`
- [Concepts](concepts.md) — workspaces, tickets, agents, events, criteria
- [Quickstart](quickstart.md) — zero to first agent reporting
