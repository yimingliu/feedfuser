*feedfuser* is a Python feed server that enables various ways of ingesting, combining, filtering, munging, and re-outputting of RSS and Atom feeds.

Currently, this only includes the use cases of:

*  concatenating multiple RSS and Atom feeds, sorting all of the entries together reverse-chronologically, and outputting common-denominator elements as a combined Atom feed
*  filtering away certain entries based on text within entry fields, such as the name of an entry's author


# Prerequisites

Python 2.7

* [futures](https://pypi.python.org/pypi/futures) -- the backport of concurrent.futures from Python 3
* [requests](https://pypi.python.org/pypi/requests) -- HTTP library for human beings
* [feedparser](https://pypi.python.org/pypi/feedparser) -- the definitive Python parser for all things feed-related
* [flask](https://pypi.python.org/pypi/Flask) -- the sanest Python web framework

I really should put together a pip package at some point.

# Installation

Git clone this repo somewhere.  For development, run the standard Flask server:

    python feedfuser.py

For deployment, see [Flask deployment](http://flask.pocoo.org/docs/0.10/deploying/)

Included is a passenger_wsgi.py file for use with Phusion Passenger's Python support.  Just need to change the second line to the python interpreter being used under virtualenv (you are using virtualenv, aren't you?)

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

The filename becomes the unique identifier for the feed.  The corresponding feed for test.json can be accessed from:

    http://127.0.0.1:5000/feeds/test
    
The definition file supports the use of filters, which acts upon entries in a feed.  The other sample file demonstrates the syntax for filter definitions.  Currently the only filters supported are "block", aka a blacklist, which excludes matching entries based on criteria set in the filter, and "allow", which includes matching entries like a whitelist.  

The only rule supported by the filter is "contains", or whether a field contains the substring given.



# Notes
feed parsing operations are in lib/feedops.py.  Concatenated feeds will spin up multiple processes to download all component feeds  in parallel.  As a result, this server is not production ready (if that wasn't obvious already from all the unimplemented parts).

# LICENSE

BSD license

Copyright (c) 2015, Yiming Liu
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
