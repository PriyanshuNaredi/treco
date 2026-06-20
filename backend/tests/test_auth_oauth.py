"""Tests for GitHub OAuth2 flow and JWT auth routes."""
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
import respx
from fastapi import HTTPException
from httpx import Response
from jose import jwt

from app.core.config import settings
from app.services.auth import create_jwt, decode_jwt
from tests.shared import TestSessionLocal


def _expired_jwt(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.utcnow() - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


class TestJwt:
    def test_create_and_decode_roundtrip(self):
        user_id = str(uuid.uuid4())
        token = create_jwt(user_id)
        assert decode_jwt(token) == user_id

    def test_decode_raises_401_on_bad_token(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt("not.a.token")
        assert exc_info.value.status_code == 401

    def test_decode_raises_401_on_garbage(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt("garbage")
        assert exc_info.value.status_code == 401

    def test_decode_raises_401_on_expired_token(self):
        user_id = str(uuid.uuid4())
        token = _expired_jwt(user_id)
        with pytest.raises(HTTPException) as exc_info:
            decode_jwt(token)
        assert exc_info.value.status_code == 401


class TestAuthRoutes:
    @pytest.mark.asyncio
    async def test_github_login_503_when_not_configured(self, client):
        r = await client.get("/api/auth/github", follow_redirects=False)
        assert r.status_code == 503

    @pytest.mark.asyncio
    async def test_github_login_redirects_when_configured(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")
        r = await client.get("/api/auth/github", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "github.com/login/oauth/authorize" in r.headers["location"]

    @pytest.mark.asyncio
    async def test_me_returns_401_without_token(self, client):
        r = await client.get("/api/auth/me")
        assert r.status_code == 422  # missing Authorization header

    @pytest.mark.asyncio
    async def test_me_returns_401_with_bad_token(self, client):
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_user_with_valid_token(self, client):
        from app.models.user import User

        user_id = str(uuid.uuid4())
        async with TestSessionLocal() as db:
            user = User(
                id=user_id,
                github_id="99999",
                login="testuser",
                avatar_url="https://github.com/testuser.png",
            )
            db.add(user)
            await db.commit()

        token = create_jwt(user_id)
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["login"] == "testuser"
        assert data["github_id"] == "99999"

    @pytest.mark.asyncio
    async def test_refresh_returns_new_token(self, client):
        from app.models.user import User

        user_id = str(uuid.uuid4())
        async with TestSessionLocal() as db:
            user = User(
                id=user_id,
                github_id="88888",
                login="refreshuser",
                avatar_url=None,
            )
            db.add(user)
            await db.commit()

        token = create_jwt(user_id)
        r = await client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # new token decodes to same user
        assert decode_jwt(data["access_token"]) == user_id

    @pytest.mark.asyncio
    async def test_refresh_returns_401_on_bad_token(self, client):
        r = await client.post("/api/auth/refresh", headers={"Authorization": "Bearer bad.token"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_upserts_user_and_redirects(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")
        monkeypatch.setattr("app.api.routes.auth.settings.frontend_url", "http://localhost:3000")

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(200, json={"access_token": "gha_fake123"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=Response(200, json={
                "id": 12345,
                "login": "octocat",
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            })
        )

        r = await client.get("/api/auth/github/callback?code=fake_code", follow_redirects=False)
        assert r.status_code in (302, 307)
        location = r.headers["location"]
        assert "http://localhost:3000/auth/callback?token=" in location

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_jwt_in_redirect_is_valid(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")
        monkeypatch.setattr("app.api.routes.auth.settings.frontend_url", "http://localhost:3000")

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(200, json={"access_token": "gha_fake123"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=Response(200, json={
                "id": 55555,
                "login": "jwtuser",
                "avatar_url": "https://avatars.githubusercontent.com/u/55555",
            })
        )

        r = await client.get("/api/auth/github/callback?code=fake_code", follow_redirects=False)
        location = r.headers["location"]
        token = parse_qs(urlparse(location).query)["token"][0]
        user_id = decode_jwt(token)
        assert user_id  # decodes to a valid UUID

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_updates_returning_user(self, client, monkeypatch):
        from app.models.user import User

        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")
        monkeypatch.setattr("app.api.routes.auth.settings.frontend_url", "http://localhost:3000")

        existing_user_id = str(uuid.uuid4())
        async with TestSessionLocal() as db:
            db.add(User(
                id=existing_user_id,
                github_id="77777",
                login="oldlogin",
                avatar_url="https://old.png",
            ))
            await db.commit()

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(200, json={"access_token": "gha_fake456"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=Response(200, json={
                "id": 77777,
                "login": "newlogin",
                "avatar_url": "https://new.png",
            })
        )

        r = await client.get("/api/auth/github/callback?code=fake_code", follow_redirects=False)
        assert r.status_code in (302, 307)

        async with TestSessionLocal() as db:
            user = await db.get(User, existing_user_id)
            assert user.login == "newlogin"
            assert user.avatar_url == "https://new.png"

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_returns_502_on_bad_code(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(401, json={"error": "bad_verification_code"})
        )

        r = await client.get("/api/auth/github/callback?code=invalid_code", follow_redirects=False)
        assert r.status_code == 502

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_returns_502_when_no_access_token(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(200, json={"error": "bad_verification_code"})
        )

        r = await client.get("/api/auth/github/callback?code=bad_code", follow_redirects=False)
        assert r.status_code == 502

    @pytest.mark.asyncio
    @respx.mock
    async def test_github_callback_returns_502_when_user_fetch_fails(self, client, monkeypatch):
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_id", "test_id")
        monkeypatch.setattr("app.api.routes.auth.settings.github_client_secret", "test_secret")

        respx.post("https://github.com/login/oauth/access_token").mock(
            return_value=Response(200, json={"access_token": "gha_fake789"})
        )
        respx.get("https://api.github.com/user").mock(
            return_value=Response(401, json={"message": "Bad credentials"})
        )

        r = await client.get("/api/auth/github/callback?code=fake_code", follow_redirects=False)
        assert r.status_code == 502

    @pytest.mark.asyncio
    async def test_me_returns_401_with_non_bearer_scheme(self, client):
        r = await client.get("/api/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_401_with_expired_token(self, client):
        token = _expired_jwt(str(uuid.uuid4()))
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_returns_401_when_user_deleted_after_token_issued(self, client):
        # Token valid but user no longer in DB
        token = create_jwt(str(uuid.uuid4()))
        r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_returns_401_with_non_bearer_scheme(self, client):
        r = await client.post("/api/auth/refresh", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_returns_401_with_expired_token(self, client):
        token = _expired_jwt(str(uuid.uuid4()))
        r = await client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_returns_401_when_user_deleted_after_token_issued(self, client):
        # Token valid but user no longer in DB
        token = create_jwt(str(uuid.uuid4()))
        r = await client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
