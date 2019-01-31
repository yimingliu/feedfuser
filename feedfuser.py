#!/usr/bin/env python3

from flask import Flask, request, abort
import os, os.path
from werkzeug.utils import secure_filename
from lib import feedops
from feedgen.feed import FeedGenerator

app = Flask(__name__, static_folder="public")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'public')
APP_CONFIG = os.path.join(APP_ROOT, 'config')
APP_CONFIG_FEEDS = os.path.join(APP_ROOT, 'config', 'feeds')


@app.route('/')
def hello_world():
    return 'Are we still in Kansas, Toto?'


@app.route('/feeds/<feed_id>/rss')
def get_rss_feed(feed_id):
    feed_gen = make_feed(feed_id, request)
    return feed_gen.rss_str(pretty=True)

@app.route('/feeds/<feed_id>')
def get_atom_feed(feed_id):
    feed_gen = make_feed(feed_id, request)
    return feed_gen.atom_str(pretty=True)


def make_feed(feed_id, request):
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

    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.id(request.url)
    fg.title(feed.name)
    fg.author({"name":"FeedFuser"})
    fg.generator("FeedFuser")
    fg.link(href=feed_uri, rel='alternate', type="text/html")
    fg.link(href=request.url, rel='self')
    fg.description(feed.name)

    for entry in feed.entries:
        title = entry.title
        if not entry.title:
            title = entry.link

        feed_item = fg.add_entry(order='append')
        feed_item.id(entry.guid)
        feed_item.title(title)
        feed_item.updated(entry.update_date)
        feed_item.author({"name":entry.author})
        feed_item.published(entry.pub_date)
        feed_item.link(link={"href": entry.link, "rel": "alternate", "type": "text/html"})
        if entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.get("href"):
                    feed_item.enclosure(url=enclosure.get("href"), length=enclosure.get("length", 0), type=enclosure.get("type", ""))
        if entry.summary:
            feed_item.summary(entry.summary)
        if entry.content:
            # TODO: make actual content types
            feed_item.content(content=entry.content, type="text" if entry.content_type == "text/plain" else "html")

    return fg

if __name__ == '__main__':
    app.run(debug=True)
