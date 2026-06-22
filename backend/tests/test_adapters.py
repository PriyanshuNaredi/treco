import pytest
import respx
from fastapi import HTTPException
from httpx import Response

from app.services.adapters.github import GitHubIssueAdapter
from app.services.adapters.jira import JiraAdapter, _extract_adf_text
from app.services.adapters.linear import LinearAdapter


class TestJiraAdapter:
    def setup_method(self):
        self.adapter = JiraAdapter()

    def test_normalize_extracts_summary_as_title(self):
        raw = {"key": "PROJ-1", "fields": {"summary": "Fix login bug", "status": {"name": "In Progress"}, "description": None}}
        result = self.adapter.normalize(raw)
        assert result.title == "Fix login bug"
        assert result.source_id == "PROJ-1"
        assert result.status == "in_progress"

    def test_normalize_preserves_raw_body(self):
        raw = {"key": "PROJ-2", "fields": {"summary": "Test", "status": {"name": "Done"}, "description": None}}
        result = self.adapter.normalize(raw)
        assert result.body == raw

    def test_extract_adf_text_recursively_extracts_text(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Hello"}, {"type": "text", "text": " world"}]}]}
        assert _extract_adf_text(adf) == "Hello world"

    def test_unknown_status_maps_to_open(self):
        raw = {"key": "PROJ-3", "fields": {"summary": "X", "status": {"name": "Custom Status"}, "description": None}}
        result = self.adapter.normalize(raw)
        assert result.status == "open"


class TestLinearAdapter:
    def setup_method(self):
        self.adapter = LinearAdapter()

    def test_normalize_extracts_identifier(self):
        raw = {"identifier": "ENG-42", "title": "Add dark mode", "state": {"name": "In Progress"}, "description": "..."}
        result = self.adapter.normalize(raw)
        assert result.source_id == "ENG-42"
        assert result.status == "in_progress"

    def test_backlog_maps_to_open(self):
        raw = {"identifier": "ENG-1", "title": "X", "state": {"name": "Backlog"}}
        result = self.adapter.normalize(raw)
        assert result.status == "open"


class TestGitHubIssueAdapter:
    def setup_method(self):
        self.adapter = GitHubIssueAdapter()

    def test_normalize_open_issue(self):
        raw = {"number": 99, "title": "Bug report", "state": "open", "body": "Steps to reproduce..."}
        result = self.adapter.normalize(raw)
        assert result.source_id == "99"
        assert result.status == "open"
        assert result.description == "Steps to reproduce..."

    def test_closed_issue_maps_to_done(self):
        raw = {"number": 1, "title": "X", "state": "closed", "body": None}
        result = self.adapter.normalize(raw)
        assert result.status == "done"

    def test_normalize_null_body_gives_none_description(self):
        raw = {"number": 5, "title": "No body", "state": "open", "body": None}
        result = self.adapter.normalize(raw)
        assert result.description is None
        assert result.source == "github"

    def test_normalize_preserves_raw_body(self):
        raw = {"number": 7, "title": "Check body", "state": "open", "body": "desc"}
        result = self.adapter.normalize(raw)
        assert result.body == raw

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_issue_happy_path(self):
        raw = {"number": 42, "title": "Fix bug", "state": "open", "body": "Details"}
        respx.get("https://api.github.com/repos/owner/repo/issues/42").mock(
            return_value=Response(200, json=raw)
        )
        result = await self.adapter.fetch_issue("owner/repo", 42, token="ghp_test")
        assert result.source_id == "42"
        assert result.title == "Fix bug"
        assert result.status == "open"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_issue_sends_auth_header_when_token_provided(self):
        raw = {"number": 1, "title": "T", "state": "open", "body": None}
        route = respx.get("https://api.github.com/repos/owner/repo/issues/1").mock(
            return_value=Response(200, json=raw)
        )
        await self.adapter.fetch_issue("owner/repo", 1, token="ghp_mytoken")
        assert route.calls[0].request.headers["authorization"] == "token ghp_mytoken"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_issue_omits_auth_header_without_token(self):
        raw = {"number": 2, "title": "T", "state": "open", "body": None}
        route = respx.get("https://api.github.com/repos/owner/repo/issues/2").mock(
            return_value=Response(200, json=raw)
        )
        await self.adapter.fetch_issue("owner/repo", 2)
        assert "authorization" not in route.calls[0].request.headers

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_issue_404_raises_http_exception(self):
        respx.get("https://api.github.com/repos/owner/repo/issues/99").mock(
            return_value=Response(404)
        )
        with pytest.raises(HTTPException) as exc_info:
            await self.adapter.fetch_issue("owner/repo", 99, token="ghp_test")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_issues_returns_normalized_list(self):
        payload = [
            {"number": 10, "title": "Issue A", "state": "open", "body": "a"},
            {"number": 11, "title": "Issue B", "state": "closed", "body": "b"},
        ]
        respx.get("https://api.github.com/repos/owner/repo/issues").mock(
            return_value=Response(200, json=payload)
        )
        results = await self.adapter.fetch_issues("owner/repo", token="", limit=20)
        assert len(results) == 2
        assert results[0].source_id == "10"
        assert results[1].status == "done"
