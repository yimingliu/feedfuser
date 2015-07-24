import json, itertools, collections, datetime
import concurrent.futures
import requests
import feedparser


def mp_fetch(source):
    return source.fetch()


def tm_struct_to_datetime(t):
    return datetime.datetime(*t[:5]+(min(t[5], 59),))  # this is a hack to convert leap seconds into 59th second instead


class FusedFeed(object):

    def __init__(self, name, sources, filters=None):
        self.name = name
        self.sources = sources
        self.filters = filters

    def __repr__(self):
        return '%s(name="%s")' % (self.__class__.__name__, self.name.encode('utf-8'))

    @classmethod
    def load_from_spec_file(cls, spec_file_path):
        data = json.load(open(spec_file_path, "rb"))
        if not data:
            return None
        name = data.get('name')
        sources = data.get('sources')
        if sources:
            sources = SourceFeed.load_from_list(sources)
        filters = data.get('filters')
        return cls(name=name, sources=sources, filters=filters)

    def fetch(self, max_workers=5):
        feeds = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Start the load operations and mark each future with its URL
            future_feed = {executor.submit(mp_fetch, source): source for source in self.sources}
            for future in concurrent.futures.as_completed(future_feed):
                old_feed = future_feed[future]
                try:
                    new_feed = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (old_feed.uri, exc))
                else:
                    feeds.append(new_feed)
            self.sources = feeds
        return self

    @property
    def entries(self):
        combined = [source.entries for source in self.sources]
        return list(itertools.chain.from_iterable(combined))


class SourceFeed(object):

    def __init__(self, uri, **kwargs):
        self.uri = uri
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.headers = kwargs.get("headers")
        self.filters = kwargs.get("filters", [])
        self.parsed = None
        self.entries = []

    def __repr__(self):
        return '%s(uri="%s")' % (self.__class__.__name__, self.uri.encode('utf-8'))

    @classmethod
    def load_from_list(cls, lst):
        feeds = map(SourceFeed.load_from_definition, lst)
        return feeds

    @classmethod
    def load_from_definition(cls, item):
        if isinstance(item, collections.Mapping):
            uri = item.get("uri")
            filters = []
            if item.get("filters"):
                filters = FeedFilter.load_from_list(item.get("filters"))
            return SourceFeed(uri=uri, filters=filters)
        else:
            return SourceFeed(uri=item)

    def fetch(self, timeout=10):
        self.parsed = None
        self.entries = []
        args = {'timeout': timeout}
        if self.username and self.password:
            args['auth'] = (self.username, self.password)
        if self.headers:
            args['headers'] = self.headers
        try:
            r = requests.get(self.uri, **args)
        except requests.exceptions.Timeout:
            return None
        if r.text:
            parsed_feed = feedparser.parse(r.text)
        if not parsed_feed:
            return None
        self.parsed = parsed_feed
        for entry in self.parsed.entries:
            feed_item = FeedEntry.create_from_parsed_entry(entry)
            self.entries.append(feed_item)
        if self.filters:
            # TODO: apply filters to the feed
            pass
        return self


class FeedEntry(object):

    def __init__(self, **kwargs):
        self.guid = kwargs.get("guid")
        self.title = kwargs.get("title")
        self.author = kwargs.get("author")
        self.summary_type = kwargs.get("summary_type")
        self.summary = kwargs.get("summary")
        self.content_type = kwargs.get("content_type")
        self.content = kwargs.get("content")
        self.link = kwargs.get("link")
        self.pub_date = kwargs.get("pub_date")
        self.update_date = kwargs.get("update_date")

    @classmethod
    def create_from_parsed_entry(cls, entry):
        item = cls(guid=entry.guid, title=entry.get("title"), author=entry.get("author"), link=entry.get("link"))
        item.pub_date = entry.get("published_parsed")
        if item.pub_date:
            item.pub_date = tm_struct_to_datetime(item.pub_date)
            datetime.datetime(2009, 11, 8, 20, 32, 35)
        item.update_date = entry.get("updated_parsed")
        if item.update_date:
            item.update_date = tm_struct_to_datetime(item.update_date)
        if entry.get("summary_detail"):
            item.summary_type = entry.summary_detail.type
            item.summary = entry.summary
        if entry.get("content_detail"):
            item.content_type = entry.content_detail.type
            item.content = entry.content
        return item


class FeedFilter(object):

    def __init__(self, mode, filter_type, rules):
        self.mode = mode
        self.filter_type = filter_type
        self.rules = rules

    def __repr__(self):
        return '%s(mode="%s", filter_type="%s")' % (self.__class__.__name__,
                                                    self.mode.encode('utf-8'),
                                                    self.filter_type.encode('utf-8'))

    @classmethod
    def load_from_list(cls, lst):
        filters = map(FeedFilter.load_from_definition, lst)
        return filters

    @classmethod
    def load_from_definition(cls, item):
        mode = item.get("mode")
        filter_type = item.get("type")
        rules = FeedFilterRule.load_from_list(item.get("rules"))
        return FeedFilter(mode=mode, filter_type=filter_type, rules=rules)


class FeedFilterRule(object):

    def __init__(self, op, field, value):
        self.op = op
        self.field = field
        self.value = value

    def __repr__(self):
        return '%s(op="%s", field="%s", value="%s")' % (self.__class__.__name__,
                                                        self.op.encode('utf-8'),
                                                        self.field.encode('utf-8'),
                                                        self.value.encode('utf-8'))

    @classmethod
    def load_from_list(cls, lst):
        rules = map(FeedFilterRule.load_from_definition, lst)
        return rules

    @classmethod
    def load_from_definition(cls, item):
        op = item.get("op")
        field = item.get("field")
        value = item.get("value")
        return FeedFilterRule(op=op, field=field, value=value)
