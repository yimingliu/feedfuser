import json
import os
import subprocess
import sys

import feedparser
import pytest
import requests

import feedfuser
from tests.samples import ATOM, RSS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client(tmp_path, monkeypatch, web, threads):
    monkeypatch.setattr(feedfuser, "APP_CONFIG_FEEDS", str(tmp_path))
    web.add("https://example.com/feed.xml", RSS)
    web.add("https://example.org/atom.xml", ATOM)
    (tmp_path / "both.json").write_text(json.dumps(
        {"name": "Both", "sources": ["https://example.com/feed.xml", "https://example.org/atom.xml"]}))
    (tmp_path / "single.json").write_text(json.dumps(
        {"name": "Single", "sources": ["https://example.org/atom.xml"]}))
    return feedfuser.app.test_client()


def read_back(response):
    assert response.status_code == 200
    return feedparser.parse(response.data, sanitize_html=False)


def test_atom_output_merges_sources_newest_first(client):
    out = read_back(client.get("/feeds/both"))
    assert out.version == "atom10"
    assert out.feed.title == "Both"
    assert [e.id for e in out.entries] == ["tag:example.org,2026:entry-1", "post-2", "post-1"]


def test_rss_output(client):
    out = read_back(client.get("/feeds/both/rss"))
    assert out.version == "rss20"
    assert [e.title for e in out.entries] == ["Atom entry", "Second post", "First post"]


def test_output_keeps_source_html_and_resolved_links(client):
    first = {e.id: e for e in read_back(client.get("/feeds/both")).entries}["post-1"]
    assert "<script>track()</script>" in first.summary
    assert 'href="https://example.com/rel"' in first.summary
    assert first.link == "https://example.com/posts/1"


def test_single_source_feed_links_to_source_site(client):
    out = read_back(client.get("/feeds/single"))
    assert out.feed.link == "https://example.org/"


@pytest.mark.parametrize("path", ["/feeds/missing", "/feeds/..%2Fboth", "/feeds/missing/rss"])
def test_unknown_feed_is_404(client, path):
    assert client.get(path).status_code == 404


def write_feed(client, tmp_path, name, sources):
    (tmp_path / (name + ".json")).write_text(json.dumps({"name": name, "sources": sources}))


@pytest.mark.parametrize("path", ["/feeds/dead", "/feeds/dead/rss"])
def test_feed_with_all_sources_failing_is_502(client, tmp_path, web, path):
    web.add("https://example.net/blocked.xml", "nope", status_code=403)
    web.fail("https://example.net/down.xml", requests.exceptions.SSLError("bad cert"))
    write_feed(client, tmp_path, "dead", ["https://example.net/blocked.xml", "https://example.net/down.xml"])
    assert client.get(path).status_code == 502


def test_feed_with_some_sources_failing_still_serves_the_rest(client, tmp_path, web):
    web.add("https://example.net/blocked.xml", "nope", status_code=403)
    write_feed(client, tmp_path, "partial", ["https://example.net/blocked.xml", "https://example.org/atom.xml"])
    assert [e.title for e in read_back(client.get("/feeds/partial")).entries] == ["Atom entry"]


def test_feed_emptied_by_filters_is_still_200(client, tmp_path):
    block_all = {"mode": "OR", "type": "block", "rules": [{"op": "contains", "field": "title", "value": "Atom"}]}
    write_feed(client, tmp_path, "filtered", [{"uri": "https://example.org/atom.xml", "filters": [block_all]}])
    assert read_back(client.get("/feeds/filtered")).entries == []


def run_python(code, **env):
    return subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True, text=True,
                          env={**os.environ, **env})


def test_passenger_runs_app_under_app_interpreter():
    result = run_python("import passenger_wsgi; print(passenger_wsgi.application.name)",
                        APP_INTERPRETER=sys.executable)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "feedfuser"


def test_app_does_not_import_cgi():
    # cgi was removed in Python 3.13.
    result = run_python("import sys, feedfuser; print('cgi' in sys.modules)")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
