RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
<channel>
  <title>Example RSS</title>
  <link>https://example.com/</link>
  <item>
    <title>First post</title>
    <link>/posts/1</link>
    <guid>post-1</guid>
    <dc:creator>Alice</dc:creator>
    <pubDate>Tue, 06 Oct 2026 10:00:00 GMT</pubDate>
    <description><![CDATA[<p onclick="track()" data-id="7" style="position: fixed">Hi <script>track()</script><a href="/rel">rel</a> <iframe src="https://video.example/embed/1"></iframe></p>]]></description>
    <enclosure url="https://example.com/a.mp3" length="1234" type="audio/mpeg"/>
  </item>
  <item>
    <title>Second post</title>
    <link>https://example.com/posts/2</link>
    <guid isPermaLink="false">post-2</guid>
    <dc:creator>Bob</dc:creator>
    <pubDate>Wed, 07 Oct 2026 10:00:00 GMT</pubDate>
    <description>Plain text from Bob</description>
  </item>
</channel>
</rss>"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>tag:example.org,2026:feed</id>
  <title>Example Atom</title>
  <link rel="alternate" href="https://example.org/"/>
  <updated>2026-10-08T12:00:00Z</updated>
  <entry>
    <id>tag:example.org,2026:entry-1</id>
    <title>Atom entry</title>
    <author><name>Carol</name></author>
    <link rel="alternate" href="/entries/1"/>
    <published>2026-10-01T08:00:00Z</published>
    <updated>2026-10-08T12:00:00Z</updated>
    <summary>Short summary</summary>
    <content type="html">&lt;p&gt;Body with &lt;img src="/img/1.png"&gt;&lt;/p&gt;</content>
  </entry>
</feed>"""

LATIN1 = """<?xml version="1.0" encoding="iso-8859-1"?>
<rss version="2.0">
<channel>
  <title>Café</title>
  <link>https://example.net/</link>
  <item><guid>l-1</guid><title>été über</title></item>
</channel>
</rss>"""


def rss(*items, link="https://example.com/"):
    """Wrap <item> XML strings in a minimal RSS 2.0 document."""
    return ('<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>t</title>'
            f'<link>{link}</link>{"".join(items)}</channel></rss>')
