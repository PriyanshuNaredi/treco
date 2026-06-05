import pytest

from app.services.criteria_extractor import _parse_checkboxes


def test_parse_checkboxes_unchecked():
    desc = "- [ ] User can log in\n- [ ] User sees dashboard"
    result = _parse_checkboxes(desc)
    assert len(result) == 2
    assert result[0]["text"] == "User can log in"
    assert result[0]["done"] is False


def test_parse_checkboxes_checked():
    desc = "- [x] Feature is behind flag\n- [ ] Tests pass"
    result = _parse_checkboxes(desc)
    assert result[0]["done"] is True
    assert result[1]["done"] is False


def test_parse_checkboxes_each_has_unique_id():
    desc = "- [ ] A\n- [ ] B\n- [ ] C"
    result = _parse_checkboxes(desc)
    ids = [c["id"] for c in result]
    assert len(set(ids)) == 3


def test_parse_checkboxes_empty_description():
    assert _parse_checkboxes("No checkboxes here") == []
