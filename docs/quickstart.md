# Quickstart — First Agent Reporting in 5 Minutes

Get Treco running locally and watch your first agent report live events to the dashboard.

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the dashboard)

---

## Step 1 — Install the SDK

```bash
pip install treco
```

This gives you the `treco` CLI and the Python SDK.

---

## Step 2 — Start the backend

```bash
treco server start
```

Starts the FastAPI backend as a background daemon on port 8001. The dashboard is served at `http://localhost:8001`.

To verify it's up:

```bash
treco server status
```

---

## Step 3 — Initialize your workspace

```bash
treco init
```

Interactive prompts:

```
Treco URL [http://localhost:8001]: ↵
Workspace ID [demo]:              ↵
```

This creates `~/.treco/config.json` with your API key, and installs Claude Code hooks into `~/.claude/settings.json` so usage is tracked automatically.

---

## Step 4 — Create your first ticket

**Option A — create manually:**

```bash
treco new "Add retry logic to payment processor"
```

Add acceptance criteria as markdown checkboxes in the description and Treco extracts them automatically:

```
Description: - [ ] Retry on 5xx up to 3 times
             - [ ] Exponential backoff with jitter
             - [ ] Log each retry attempt
```

**Option B — import from GitHub:**

```bash
treco import https://github.com/your-org/your-repo/issues/42
```

Treco fetches the issue and extracts acceptance criteria from the body.

**Option C — import from Linear:**

```bash
treco import https://linear.app/your-team/issue/ENG-42
```

---

## Step 5 — Start a session

```bash
treco start
```

Pick the ticket from the list. This emits a `ticket_started` event and saves the active session locally.

---

## Step 6 — Let your agent work

### If you use Claude Code

Nothing else to do. The hooks installed in step 3 fire on every tool call, streaming token usage and tool activity to Treco automatically.

Open the dashboard at `http://localhost:8001` to watch events appear in real time.

### If you use the Python SDK

Wrap your agent logic with `TrecoClient.track()`:

```python
import asyncio
from treco import TrecoClient

TICKET_ID = "your-ticket-id"  # from `treco status`

async def run_agent():
    async with TrecoClient() as client:
        async with client.track(TICKET_ID):
            # your agent work here
            await client.log(TICKET_ID, "Starting analysis")

            # mark individual criteria done
            await client.check(
                TICKET_ID,
                criterion_id="abc123",  # from ticket detail
                tokens_in=1200,
                tokens_out=340,
            )

asyncio.run(run_agent())
```

`TrecoClient` reads `TRECO_API_KEY` and `TRECO_URL` from the environment, or from `~/.treco/config.json` if you ran `treco init`.

`track()` auto-emits `ticket_started` on enter and `done` on exit. If your code raises, it emits `error` before re-raising.

---

## Step 7 — Mark criteria done from the CLI

If you're working interactively, mark acceptance criteria done as you go:

```bash
treco check abc123   # criterion ID shown in `treco start` output
```

To see the full criterion ID list:

```bash
treco status
```

---

## Step 8 — End the session

```bash
treco done
```

Emits a `done` event with cumulative token counts and closes the session.

---

## Dashboard

Open `http://localhost:8001` to see:

- All tickets and their criteria status
- Per-ticket token usage and cost
- Live event stream per ticket

---

## What's next

- [Concepts](concepts.md) — tickets, agents, events, criteria, workspaces explained
- [CLI Reference](cli-reference.md) — every command with examples
- [SDK Reference](sdk-reference.md) — full `TrecoClient` API
- [Integrations](integrations/) — Jira, Linear, Asana, GitHub setup
- [Self-hosting](self-hosting.md) — Docker and PostgreSQL for production
