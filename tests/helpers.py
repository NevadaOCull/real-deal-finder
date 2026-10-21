from pathlib import Path

from dealfinder.fetch import SourceError

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def fake_fetch(pages):
    """A stand-in for dealfinder.fetch.fetch. Keys are URL substrings; values are bodies or exceptions."""
    calls = []

    def fetch(url):
        calls.append(url)
        for key, body in pages.items():
            if key in url:
                if isinstance(body, Exception):
                    raise body
                return body
        raise SourceError(f"no fake page for {url}")

    fetch.calls = calls
    return fetch
