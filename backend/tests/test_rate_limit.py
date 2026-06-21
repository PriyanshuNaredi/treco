"""Rate limiting middleware tests."""
import pytest
from httpx import ASGITransport, AsyncClient
from limits import parse
from unittest.mock import patch

import app.core.limiter as rl_module
from app.main import app


@pytest.fixture(autouse=True)
def reset_storage():
    rl_module.reset_limits()
    yield
    rl_module.reset_limits()


@pytest.mark.asyncio
async def test_api_route_allows_request_within_limit(client):
    resp = await client.get("/api/agents")
    assert resp.status_code != 429


@pytest.mark.asyncio
async def test_health_endpoint_exempt_from_rate_limit(client):
    with patch.object(rl_module, "_strategy") as mock:
        mock.hit.return_value = False
        resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_429_when_strategy_denies(client):
    with patch.object(rl_module, "_strategy") as mock:
        mock.hit.return_value = False
        resp = await client.get("/api/agents")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Rate limit exceeded"
    assert resp.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_uses_api_key_identifier_when_header_present(agent_with_key):
    agent, raw_key = agent_with_key
    with patch.object(rl_module, "_strategy") as mock:
        mock.hit.return_value = True
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/agents/me", headers={"X-Agent-Key": raw_key})
        _, identifier = mock.hit.call_args[0]
        assert identifier == f"key:{raw_key}"


@pytest.mark.asyncio
async def test_uses_ip_identifier_when_no_key(client):
    with patch.object(rl_module, "_strategy") as mock:
        mock.hit.return_value = True
        await client.get("/api/agents")
        _, identifier = mock.hit.call_args[0]
        assert identifier.startswith("ip:")


@pytest.mark.asyncio
async def test_ip_limit_counter_enforced():
    original = rl_module._ip_limit
    rl_module._ip_limit = parse("3/minute")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            for _ in range(3):
                r = await c.get("/api/agents")
                assert r.status_code != 429
            r = await c.get("/api/agents")
            assert r.status_code == 429
    finally:
        rl_module._ip_limit = original


@pytest.mark.asyncio
async def test_key_limit_counter_enforced(agent_with_key):
    agent, raw_key = agent_with_key
    original = rl_module._key_limit
    rl_module._key_limit = parse("3/minute")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            for _ in range(3):
                r = await c.get("/api/agents/me", headers={"X-Agent-Key": raw_key})
                assert r.status_code != 429
            r = await c.get("/api/agents/me", headers={"X-Agent-Key": raw_key})
            assert r.status_code == 429
    finally:
        rl_module._key_limit = original


@pytest.mark.asyncio
async def test_key_and_ip_buckets_are_independent(agent_with_key):
    """IP exhaustion must not affect key-authenticated requests."""
    agent, raw_key = agent_with_key
    original_ip = rl_module._ip_limit
    original_key = rl_module._key_limit
    rl_module._ip_limit = parse("2/minute")
    rl_module._key_limit = parse("10/minute")
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # Exhaust IP bucket
            for _ in range(2):
                await c.get("/api/agents")
            r = await c.get("/api/agents")
            assert r.status_code == 429

            # Key bucket unaffected
            r = await c.get("/api/agents/me", headers={"X-Agent-Key": raw_key})
            assert r.status_code != 429
    finally:
        rl_module._ip_limit = original_ip
        rl_module._key_limit = original_key
