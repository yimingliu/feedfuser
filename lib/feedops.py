import json, itertools, collections, datetime
import concurrent.futures
import requests
import feedparser
import hashlib


def mp_fetch(source):
    # wrapper: multiprocessing does not like classes and class methods. top-level only
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
            future_feed = {executor.submit(mp_fetch, source): source for source in self.sources}
            for future in concurrent.futures.as_completed(future_feed):
                old_feed = future_feed[future]
                try:
                    new_feed = future.result(timeout=10)
                except Exception as exc:
                    print('%r generated an exception: %s' % (old_feed.uri, exc))
                else:
                    if new_feed:
                        feeds.append(new_feed)
            self.sources = feeds
        return self

    @property
    def entries(self):
        combined = [source.entries for source in self.sources]
        entries = list(itertools.chain.from_iterable(combined))
        entries.sort(key=lambda entry: entry.update_date, reverse=True)
        return entries

    @property
    def cache_info(self):
        return {feed.uri:{'etag':feed.etag, 'last-modified':feed.last_modified} for feed in self.sources}


class SourceFeed(object):

    def __init__(self, uri, **kwargs):
        self.uri = uri
        self.html_uri = kwargs.get("html_uri")
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")
        self.headers = kwargs.get("headers", {})
        self.filters = kwargs.get("filters", [])
        self.parsed = None
        self.entries = []
        self.etag = None
        self.last_modified = None
        self.raw = None

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
        args['headers'] = self.headers
        if self.etag:
            args['headers']['If-None-Match'] = self.etag
        if self.last_modified:
            args['headers']['If-Modified-Since'] = self.last_modified
        try:
            #print args
            r = requests.get(self.uri, **args)
            #print r.request.headers
        except requests.exceptions.Timeout:
            return None
        print self.uri, " status", r.status_code
        if 300 > r.status_code >= 200:
            print r.headers.get("etag")
            if r.text:
                parsed_feed = feedparser.parse(r.text)
                self.raw = r.text
            if not parsed_feed or parsed_feed.get("bozo_exception"):
                # can't parse whatever text is available, return nothing.
                print self.uri, " failed to parse feed.  Returning nothing"
                return None
        elif r.status_code == 304:
            if self.raw:
                # assume that if we already have text that this is reusing a cached object; just reparse the old text
                parsed_feed = feedparser.parse(self.raw)
            else:
                # we don't have cached text and the server 304s.  We shouldn't have used the ETag/Last-Modified; return with nothing
                print self.uri, " returning fail"
                return None
        else:
            print self.uri, "utter fail"
            # a 400+ code (or a 30x redirect, which shouldn't happen)
            return None
        if r.headers.get('etag'):
            self.etag = r.headers.get('etag') # overwrite the old cache data with the new ones
        if r.headers.get("last-modified"):
            self.last_modified = r.headers.get("last-modified")
        #self.parsed = parsed_feed
        self.html_uri = parsed_feed.feed.link
        for entry in parsed_feed.entries:
            feed_item = FeedEntry.create_from_parsed_entry(entry)
            if feed_item:
                self.entries.append(feed_item)
        if self.filters:
            for fil in self.filters:
                self.entries = fil.apply(self.entries)
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

    def __repr__(self):
        return "<FeedEntry link='%s'>" % (self.link.encode('utf-8'))

    @classmethod
    def create_from_parsed_entry(cls, entry):
        item = cls(guid=entry.guid, title=entry.get("title"), author=entry.get("author"), link=entry.get("link"))
        item.pub_date = entry.get("published_parsed")
        if item.pub_date:
            item.pub_date = tm_struct_to_datetime(item.pub_date)
        item.update_date = entry.get("updated_parsed")
        if item.update_date:
            item.update_date = tm_struct_to_datetime(item.update_date)
        if not item.update_date:
            item.update_date = datetime.datetime.now()
        if entry.get("summary_detail"):
            item.summary_type = entry.summary_detail.type
            item.summary = entry.summary
        if entry.get("content"):
            item.content_type = entry.content[0].type
            item.content = entry.content[0].value
        if not item.guid:
            item_stuff = ""
            if item.title:
                item_stuff += item.title
            if item.content:
                item_stuff += item.content
            if item.summary:
                item_stuff += item.summary
            if item_stuff:
                item.guid = hashlib.md5(item_stuff).hexdigest()
            else:
                return None # this can't possibly be a valid entry
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
        return FeedFilter.make_filter(mode=mode, filter_type=filter_type, rules=rules)

    @classmethod
    def make_filter(cls, filter_type, mode, rules):
        if filter_type == "block":
            return FeedFilterBlock(mode=mode, rules=rules)
        else:
            return FeedFilter(mode=mode, filter_type=filter_type, rules=rules)

    def apply(self, entries):
        return entries


class FeedFilterBlock(FeedFilter):

    def __init__(self, mode, rules):
        super(FeedFilterBlock, self).__init__(filter_type="block", mode=mode, rules=rules)

    def apply(self, entries):
        results = []
        for entry in entries:
            if self.mode.lower() == "or":  # if an entry matches any of the rules, exclude it
                for rule in self.rules:
                    if rule.apply(entry):
                        # one of the rules matched -- exclude it
                        break
                else:
                    results.append(entry)
            elif self.mode.lower() == "and":  # entry must match against all rules to be excluded
                for rule in self.rules:
                    if not rule.apply(entry):
                        # one of the rules didn't match -- should not be excluded
                        results.append(entry)
                        break
        return results


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
        return FeedFilterRule.make_rule(op=op, field=field, value=value)

    @classmethod
    def make_rule(cls, op, field, value):
        if op.lower() == "contains":
            return FeedFilterRuleContains(field=field, value=value)
        else:
            return FeedFilterRule(op=op, field=field, value=value)

    def apply(self, entry):
        return False


class FeedFilterRuleContains(FeedFilterRule):

    def __init__(self, field, value):
        super(FeedFilterRuleContains, self).__init__(op="contains", field=field, value=value)

    def apply(self, entry):
        if hasattr(entry, self.field) and self.value:
            text = getattr(entry, self.field)
            if text.find(self.value) != -1:
                return True
        return False

