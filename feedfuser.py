from flask import Flask, abort
import os, os.path
from werkzeug.utils import secure_filename
from werkzeug.contrib.atom import AtomFeed
from lib import feedops

app = Flask(__name__, static_folder="public")
APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'public')
APP_CONFIG = os.path.join(APP_ROOT, 'config')
APP_CONFIG_FEEDS = os.path.join(APP_ROOT, 'config', 'feeds')


@app.route('/')
def hello_world():
    return 'Hello World!'


@app.route('/feeds/<feed_id>')
def get_feed(feed_id):
    feed_id = secure_filename(feed_id)
    feed_config_filepath = os.path.join(APP_CONFIG_FEEDS, feed_id+".json")
    if not os.path.isfile(feed_config_filepath):
        print feed_config_filepath
        abort(404)
    feed = feedops.FusedFeed.load_from_spec_file(feed_config_filepath)
    feed.fetch()
    return str(feed.sources)

if __name__ == '__main__':
    app.run()

#feed = AtomFeed('Recent Articles',
#                     feed_url=request.url, url=request.url_root)
# articles = Article.query.order_by(Article.pub_date.desc()) \
#     .limit(15).all()
# for article in articles:
#     feed.add(article.title, unicode(article.rendered_text),
#              content_type='html',
#              author=article.author.name,
#              url=make_external(article.url),
#              updated=article.last_update,
#              published=article.published)
# return feed.get_response()