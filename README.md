
# Squidpeek

## About Squidpeek

This is a quick and dirty script for getting cool per-URL statistics and sparklines out of your Squid access logs.

Because it's per-URL, it's most appropriate for use with gateways (aka "reverse proxies").

## Requirements and Installation

Squidpeek needs Python 2.5 or greater; see <http://python.org/>. 

You'll also need the Python Imaging Library (PIL); see <http://www.pythonware.com/products/pil/>.

The easy way to install is with pip;

> pip install squidpeek

Obviously, you also need some Squid logs; see <http://squid-cache.org/>. Other programs that generate Squid logs (e.g., Traffic Server) may or may not work, depending on how faithfully they follow the format's semantics.

Finally, you'll need a browser that can handle data: URLs. Note that less-than-recent versions of IE can't do this.


## Using Squidpeek

The command-line interface is like this:

> % squidpeek.py [-q] [-n num] logfile
>   -q  use the query string as part of the URI
>   -n [num] show the top num URLs (default: 100)

Typically, you'd use squidpeek in a cron job, like this:

> # run once an hour; assumes logs are rotated right beforehand
> 2 * * * * root squidpeek /var/log/squid/access_log

## Support and Contributions

Please feel free to file issues above; this code doesn't see a lot of maintenance, so I can't promise a quick response.

All input is welcome, particularly code contributions via a Github pull request. 

Maintainer: Mark Nottingham <mnot@mnot.net>


# License

Copyright (c) 2011 Mark Nottingham

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.