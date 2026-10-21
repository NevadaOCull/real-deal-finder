from urllib.parse import urlparse

import requests

# CamelCamelCamel blocks the longer "(KHTML, like Gecko) Chrome/130.0" form of this.
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"


class SourceError(Exception):
    """A store or site couldn't be read. The message is shown to the owner."""


def fetch(url: str, timeout: float = 20) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        })
    except requests.RequestException as e:
        raise SourceError(f"couldn't reach {host} ({e.__class__.__name__})") from None
    if response.status_code in (403, 429, 503):
        raise SourceError(f"{host} blocked the check (error {response.status_code})")
    if response.status_code != 200:
        raise SourceError(f"{host} answered with error {response.status_code}")
    return response.text
