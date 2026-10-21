import pytest
import requests

from dealfinder import fetch as fetch_module
from dealfinder.fetch import SourceError, fetch


class FakeResponse:
    def __init__(self, status, text="ok"):
        self.status_code = status
        self.text = text


def test_returns_text_on_200(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(200, "hello"))
    assert fetch("https://drifthq.com/x") == "hello"


def test_blocked_status_is_source_error(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(403))
    with pytest.raises(SourceError, match="homedepot.com blocked the check"):
        fetch("https://www.homedepot.com/p/1")


def test_other_status_is_source_error(monkeypatch):
    monkeypatch.setattr(fetch_module.requests, "get", lambda url, **kw: FakeResponse(404))
    with pytest.raises(SourceError, match="error 404"):
        fetch("https://drifthq.com/x")


def test_network_problem_is_source_error(monkeypatch):
    def boom(url, **kw):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(fetch_module.requests, "get", boom)
    with pytest.raises(SourceError, match="couldn't reach drifthq.com"):
        fetch("https://drifthq.com/x")
