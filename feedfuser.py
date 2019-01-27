#!/usr/bin/env python3

from flask import Flask, request, abort
import os, os.path
from werkzeug.utils import secure_filename
from werkzeug.contrib.atom import AtomFeed, FeedEntry
from lib import feedops

app = Flask(__name__, static_folder="public")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'public')
APP_CONFIG = os.path.join(APP_ROOT, 'config')
APP_CONFIG_FEEDS = os.path.join(APP_ROOT, 'config', 'feeds')


@app.route('/')
def hello_world():
    return 'Are we still in Kansas, Toto?'


@app.route('/feeds/<feed_id>')
def get_feed(feed_id):
    feed_id = secure_filename(feed_id)
    feed_config_filepath = os.path.join(APP_CONFIG_FEEDS, feed_id+".json")
    if not os.path.isfile(feed_config_filepath):
        # print(feed_config_filepath)
        abort(404)
    feed = feedops.FusedFeed.load_from_spec_file(feed_config_filepath)
    if not feed:
        abort(400)
    feed.fetch()
    feed_uri = request.url_root
    if len(feed.sources) == 1:
        # if there is only 1 source in a fusedfeed
        # just give the feed's html alternate
        # TODO: instead, we should generate our own HTML representation
        feed_uri = feed.sources[0].html_uri
    output = AtomFeed(feed.name, feed_url=request.url, author="FeedFuser", links=[{"href": feed_uri,
                                                                                   "rel": "alternate",
                                                                                   "type": "text/html"}])
    for entry in feed.entries:
        title = entry.title
        if not entry.title:
            title = entry.link
        links = [{"href": entry.link, "rel": "alternate","type": "text/html"}]
        if entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get("href"):
                    links.append({"rel":"enclosure", "href":enclosure.get("href"), "type":enclosure.get("type", ""), "length":enclosure.get("length", 0)})
        feed_item = FeedEntry(id=entry.guid, title=title, updated=entry.update_date,
                              author=entry.author, published=entry.pub_date, links=links)

        if entry.summary:
            feed_item.summary = entry.summary
            feed_item.summary_type = "text" if entry.summary_type == "text/plain" else "html"
        if entry.content:
            feed_item.content = entry.content
            feed_item.content_type = "text" if entry.content_type == "text/plain" else "html"
        output.add(feed_item)
    return output.get_response()
    # return str(feed.sources)


if __name__ == '__main__':
    app.run(debug=True)
