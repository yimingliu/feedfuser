*feedfuser* is a Python feed server that enables various ways of ingesting, combining, filtering, munging, and re-outputting of RSS and Atom feeds.

Currently, this only includes the use cases of:

*  concatenating multiple RSS and Atom feeds, sorting all of the entries together reverse-chronologically, and outputting common-denominator elements as a combined Atom or RSS 2.0 feed
*  filtering away certain entries based on text within entry fields, such as the name of an entry's author


# Prerequisites

Python 3.x

* [requests](https://pypi.python.org/pypi/requests) -- HTTP library for human beings
* [flask](https://pypi.python.org/pypi/Flask) -- the sanest Python web framework
* [python-feedgen](https://github.com/lkiesow/python-feedgen) -- replaces the deprecated AtomFeed component in Flask
* [feedparser](https://pypi.python.org/pypi/feedparser) -- the definitive Python parser for all things feed-related
* [parsel](https://github.com/scrapy/parsel) -- XPath parsing

I really should put together a pip package at some point.

# Installation

Git clone this repo somewhere.  

Install the prerequisites via 

    pip install -r requirements.txt

For development, run the standard Flask server:

    python feedfuser.py
    
If used on macOS, it is possible to run into a python [multiprocessing crash](https://blog.yimingliu.com/2015/07/22/python-multiprocessing-code-crashes-on-os-x-under-ipython/) bug.  If this happens, run instead with:

    env no_proxy='*' python feedfuser.py

For deployment, see [Flask deployment](http://flask.pocoo.org/docs/0.10/deploying/)

Included is a `passenger_wsgi.py` file for use with Phusion Passenger's Python support.  Just need to change the second line to the python interpreter being used under virtualenv (you are using virtualenv, aren't you?)

# Usage

This is intended to be a personal feed server for someone who can host their own Python webapps.  To create a new feed, you need to create a feed definition JSON file and put it in:

    $FEEDFUSERDIR/config/feeds/
   
In the simplest case (concatenating multiple feeds), a listing of URIs in sources (or using a hash containing only the "uri" key) is sufficient:

    {
        "name":"Berkeley News",

        "sources":
        [
            "http://www.berkeleyside.com/feed/atom/",
            {"uri":"http://www.dailycal.org/feed/"}
        ]

    }

The filename becomes the unique identifier for the feed.  The corresponding Atom feed for test.json can be accessed from:

    http://127.0.0.1:5000/feeds/test
    
The corresponding RSS 2.0 feed is available from:

    http://127.0.0.1:5000/feeds/test/rss
    
The definition file supports the use of filters, which acts upon entries in a feed.  The other sample file demonstrates the syntax for filter definitions.  Currently the only filters supported are "block", aka a blacklist, which excludes matching entries based on criteria set in the filter, and "allow", which includes matching entries like a whitelist.  

The two rules supported by the filter are:
- "contains" -- whether a field contains the substring given
- "xpath" -- any valid XPath 1.0 expression (currently the only kind of XPath supported by `parsel`).  This assumes the field being processed is a sufficiently well-formed HTML/XML fragment that can be parsed by `parsel`


# Other Notes

Feed parsing rules and filters are in lib/feedops.py.  

Concatenated feeds will spin up multiple processes to download all component feeds  in parallel, which may be a lot of processes.

# LICENSE

BSD license

Copyright (c) 2015-2019, Yiming Liu
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
