import datetime
import hashlib

import requests
from feedparser.mixin import _FeedParserMixin

from lib import feedops
from tests.samples import ATOM, LATIN1, RSS, rss

UTC = datetime.timezone.utc
FEED_URL = "https://example.com/feed.xml"


def fetch(web, text, uri=FEED_URL, url=None, **kwargs):
    web.add(uri, text, url=url, **kwargs)
    return feedops.SourceFeed(uri=uri).fetch()


def by_guid(source):
    return {entry.guid: entry for entry in source.entries}


# Standard parsing

def test_rss_entry_fields(web):
    source = fetch(web, RSS)
    first = by_guid(source)["post-1"]
    assert first.title == "First post"
    assert first.author == "Alice"
    assert first.pub_date == datetime.datetime(2026, 10, 6, 10, tzinfo=UTC)
    assert first.update_date == first.pub_date
    assert first.summary_type == "text/html"
    assert first.enclosures[0]["href"] == "https://example.com/a.mp3"
    assert first.enclosures[0]["type"] == "audio/mpeg"
    assert source.html_uri == "https://example.com/"
    assert len(source.entries) == 2


def test_atom_entry_fields(web):
    source = fetch(web, ATOM, uri="https://example.org/atom.xml")
    [entry] = source.entries
    assert entry.guid == "tag:example.org,2026:entry-1"
    assert entry.title == "Atom entry"
    assert entry.author == "Carol"
    assert entry.pub_date == datetime.datetime(2026, 10, 1, 8, tzinfo=UTC)
    assert entry.update_date == datetime.datetime(2026, 10, 8, 12, tzinfo=UTC)
    assert entry.summary == "Short summary"
    assert entry.content_type == "text/html"
    assert source.html_uri == "https://example.org/"


def test_undated_entry_gets_current_time(web):
    before = datetime.datetime.now(UTC)
    [entry] = fetch(web, rss("<item><guid>x</guid><title>Undated</title></item>")).entries
    assert entry.pub_date is None
    assert before <= entry.update_date <= datetime.datetime.now(UTC)


def test_declared_latin1_encoding_is_honored(web):
    source = fetch(web, LATIN1)
    assert source is not None
    assert source.entries[0].title == "été über"


def test_http_error_returns_none(web):
    assert fetch(web, RSS, status_code=500) is None


def test_unparseable_feed_returns_none(web):
    assert fetch(web, "<rss><channel><item>&undefined;</item></channel></rss>") is None
    assert fetch(web, "", uri="https://example.com/empty") is None


def test_timeout_returns_none(web):
    web.fail(FEED_URL, requests.exceptions.Timeout())
    assert feedops.SourceFeed(uri=FEED_URL).fetch() is None


def test_conditional_get_and_304_reuses_cached_text(web):
    source = feedops.SourceFeed(uri=FEED_URL)
    web.add(FEED_URL, RSS, headers={"ETag": '"v1"', "Last-Modified": "Tue, 06 Oct 2026 10:00:00 GMT"})
    source.fetch()
    web.add(FEED_URL, "", status_code=304)
    assert source.fetch() is source
    assert web.requests[-1][1]["If-None-Match"] == '"v1"'
    assert web.requests[-1][1]["If-Modified-Since"] == "Tue, 06 Oct 2026 10:00:00 GMT"
    assert set(by_guid(source)) == {"post-1", "post-2"}


def test_304_without_cached_text_returns_none(web):
    assert fetch(web, "", status_code=304) is None


# Source HTML is passed through unsanitized

def test_html_is_not_sanitized(web):
    summary = by_guid(fetch(web, RSS))["post-1"].summary
    for kept in ('onclick="track()"', "<script>track()</script>", "<iframe", 'data-id="7"', "position: fixed"):
        assert kept in summary


# Relative URLs resolve against the final response URL

def test_relative_links_resolve_against_response_url(web):
    source = fetch(web, RSS, uri="http://example.com/feed", url="https://www.example.com/feed.xml")
    first = by_guid(source)["post-1"]
    assert 'href="https://www.example.com/rel"' in first.summary
    assert first.link == "https://www.example.com/posts/1"


def test_relative_links_in_atom_content_resolve(web):
    [entry] = fetch(web, ATOM, uri="https://example.org/atom.xml").entries
    assert 'src="https://example.org/img/1.png"' in entry.content
    assert entry.link == "https://example.org/entries/1"


# Guids are identifiers and are never rewritten as URLs

def test_permalink_guid_is_not_resolved(web):
    entries = by_guid(fetch(web, RSS))
    assert set(entries) == {"post-1", "post-2"}


def test_guid_patch_is_installed():
    assert "id" not in _FeedParserMixin.can_be_relative_uri
    assert "link" in _FeedParserMixin.can_be_relative_uri


# Entries without a guid

def test_missing_guid_falls_back_to_content_hash(web):
    item = "<item><title>No guid</title><description>Body</description></item>"
    [entry] = fetch(web, rss(item)).entries
    assert entry.guid == hashlib.md5("No guidBody".encode("utf-8")).hexdigest()
    [again] = fetch(web, rss(item), uri="https://example.com/again").entries
    assert again.guid == entry.guid


def test_entry_without_guid_or_text_is_skipped(web):
    items = rss("<item><link>https://example.com/bare</link></item>", "<item><guid>kept</guid><title>Kept</title></item>")
    assert [entry.guid for entry in fetch(web, items).entries] == ["kept"]
