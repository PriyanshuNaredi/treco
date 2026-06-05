import pytest

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
