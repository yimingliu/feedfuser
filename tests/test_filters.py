import json

import pytest

from lib import feedops
from tests.samples import rss


def entry(guid, author="", summary=""):
    return feedops.FeedEntry(guid=guid, author=author, summary=summary)


ENTRIES = [
    entry("a", author="Pat Example", summary='<p><a href="https://docs.example.com/x">fix</a></p>'),
    entry("b", author="Sam Example", summary="<p>no links</p>"),
    entry("c", author="Pat Example", summary="<p>no links</p>"),
]


def make_filter(filter_type, mode, *rules):
    return feedops.FeedFilter.load_from_definition({
        "type": filter_type,
        "mode": mode,
        "rules": [{"op": op, "field": field, "value": value} for op, field, value in rules],
    })


def guids(entries):
    return [e.guid for e in entries]


@pytest.mark.parametrize("filter_type, mode, expected", [
    ("block", "OR", ["b"]),
    ("block", "AND", ["b", "c"]),
    ("allow", "OR", ["a", "c"]),
    ("allow", "AND", ["a"]),
])
def test_filter_modes(filter_type, mode, expected):
    fil = make_filter(filter_type, mode,
                      ("contains", "author", "Pat Example"),
                      ("xpath", "summary", "//a[contains(@href, 'docs.example.com')]"))
    assert guids(fil.apply(ENTRIES)) == expected


def test_contains_is_case_sensitive():
    fil = make_filter("block", "OR", ("contains", "author", "pat example"))
    assert guids(fil.apply(ENTRIES)) == ["a", "b", "c"]


@pytest.mark.parametrize("filter_type, expected", [("block", ["none"]), ("allow", [])])
def test_contains_on_missing_field_does_not_match(filter_type, expected):
    fil = make_filter(filter_type, "OR", ("contains", "author", "Pat Example"))
    assert guids(fil.apply([feedops.FeedEntry(guid="none", author=None)])) == expected


def test_spec_file_loads_sources_and_filters(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "name": "Fused",
        "sources": [
            "https://one.example/feed",
            {"uri": "https://two.example/feed",
             "filters": [{"mode": "OR", "type": "block",
                          "rules": [{"op": "contains", "field": "author", "value": "Spam"}]}]},
        ],
        "filters": [{"mode": "OR", "type": "allow",
                     "rules": [{"op": "contains", "field": "title", "value": "keep"}]}],
    }))
    feed = feedops.FusedFeed.load_from_spec_file(str(spec))
    assert feed.name == "Fused"
    assert [s.uri for s in feed.sources] == ["https://one.example/feed", "https://two.example/feed"]
    assert feed.sources[0].filters == []
    assert isinstance(feed.sources[1].filters[0], feedops.FeedFilterBlock)
    assert isinstance(feed.filters[0], feedops.FeedFilterAllow)


def test_source_filter_applies_during_fetch(web):
    web.add("https://example.com/feed", rss(
        "<item><guid>1</guid><title>one</title><author>spam@example.com (Spam)</author></item>",
        "<item><guid>2</guid><title>two</title><author>ok@example.com (Ok)</author></item>",
        "<item><guid>3</guid><title>no author</title></item>"))
    fil = make_filter("block", "OR", ("contains", "author", "Spam"))
    source = feedops.SourceFeed(uri="https://example.com/feed", filters=[fil]).fetch()
    assert guids(source.entries) == ["2", "3"]


def test_fused_entries_are_merged_newest_first_and_feed_filters_apply(web, threads):
    web.add("https://one.example/feed", rss(
        "<item><guid>old</guid><title>keep old</title><pubDate>Mon, 05 Oct 2026 00:00:00 GMT</pubDate></item>",
        "<item><guid>drop</guid><title>drop me</title><pubDate>Thu, 08 Oct 2026 00:00:00 GMT</pubDate></item>"))
    web.add("https://two.example/feed", rss(
        "<item><guid>new</guid><title>keep new</title><pubDate>Wed, 07 Oct 2026 00:00:00 GMT</pubDate></item>"))
    web.add("https://down.example/feed", status_code=503)
    sources = [feedops.SourceFeed(uri=u) for u in
               ("https://one.example/feed", "https://two.example/feed", "https://down.example/feed")]
    feed = feedops.FusedFeed("Fused", sources, filters=[make_filter("allow", "OR", ("contains", "title", "keep"))])
    feed.fetch()
    assert len(feed.sources) == 2
    assert guids(feed.entries) == ["new", "old"]
