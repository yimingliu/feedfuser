import concurrent.futures

import pytest
from requests.structures import CaseInsensitiveDict

from lib import feedops


class FakeResponse:

    def __init__(self, text, status_code, headers, url):
        self.text = text
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(headers or {})
        self.url = url


class FakeWeb:
    """Stands in for requests.get: canned responses keyed by requested URL, plus a log of requests."""

    def __init__(self):
        self.responses = {}
        self.requests = []

    def add(self, uri, text="", status_code=200, headers=None, url=None):
        self.responses[uri] = FakeResponse(text, status_code, headers, url or uri)

    def fail(self, uri, exc):
        self.responses[uri] = exc

    def get(self, uri, **kwargs):
        self.requests.append((uri, dict(kwargs.get("headers") or {})))
        response = self.responses[uri]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def web(monkeypatch):
    fake = FakeWeb()
    monkeypatch.setattr(feedops.requests, "get", fake.get)
    return fake


@pytest.fixture
def threads(monkeypatch):
    # Worker processes would not inherit the patched requests.get, so fetch sources on threads instead.
    monkeypatch.setattr(concurrent.futures, "ProcessPoolExecutor", concurrent.futures.ThreadPoolExecutor)
