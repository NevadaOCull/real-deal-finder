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


def test_sends_a_user_agent_camelcamelcamel_accepts(monkeypatch):
    # CamelCamelCamel answers 403 to the longer "(KHTML, like Gecko) Chrome/130.0" form (checked live 2026-10-21).
    sent = {}

    def capture(url, **kw):
        sent.update(kw["headers"])
        return FakeResponse(200)
    monkeypatch.setattr(fetch_module.requests, "get", capture)
    fetch("https://camelcamelcamel.com/product/B00KCF7JL6")
    assert sent["User-Agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
