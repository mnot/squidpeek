#!/usr/bin/env python

"""
Squidpeek - Per-URL Squid Logfile Metrics

Mark Nottingham <mnot@mnot.net>
"""

__license__ = """
Copyright (c) 2006 Mark Nottingham <mnot@pobox.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__version__ = "1.5"

import sys
import os
import time
import urlparse
import urllib
import hashlib
import re
import socket
from UserDict import UserDict


max_url_len = 96


HIT = 1  # served without contacting origin server
MEMORY_HIT = 2 # HIT from memory
STALE_HIT = 3 # HIT while stale or error
MISS = 4 # some contact with origin server necessary
SERVER_VALIDATE = 5 # server tried to validate
SERVER_VALIDATE_YES = 6 # validated successfully
SERVER_FAIL = 7 # problem getting to the server
CLIENT_NOCACHE = 8 # client asked us not to
ASYNC = 9 # background fetch; not client-related
NEGATIVE_HIT = 10 # cached error
CLIENT_ERR = 11 # client-side problem   # TODO: not currently used

log_tags = {
    'TCP_HIT': [HIT],
    'TCP_MISS': [MISS],
    'TCP_REFRESH_HIT': [MISS, SERVER_VALIDATE, SERVER_VALIDATE_YES],
    'TCP_REFRESH_FAIL_HIT': [MISS, SERVER_VALIDATE, SERVER_FAIL],
    'TCP_REF_FAIL_HIT': [MISS, SERVER_VALIDATE, SERVER_FAIL],
    'TCP_REFRESH_MISS': [MISS, SERVER_VALIDATE],
    'TCP_CLIENT_REFRESH_MISS': [MISS, CLIENT_NOCACHE],
    'TCP_CLIENT_REFRESH': [MISS, CLIENT_NOCACHE],
    'TCP_IMS_HIT': [HIT],
    'TCP_IMS_MISS': [MISS], 
    'TCP_SWAPFAIL_MISS': [MISS],
    'TCP_SWAPFAIL': [MISS],
    'TCP_NEGATIVE_HIT': [HIT, NEGATIVE_HIT], 
    'TCP_MEM_HIT': [HIT, MEMORY_HIT],
    'TCP_DENIED': [CLIENT_ERR],
    'TCP_OFFLINE_HIT': [HIT],
    'NONE': [MISS, SERVER_FAIL], # ?
    'TCP_STALE_HIT': [HIT, STALE_HIT],
    'TCP_ASYNC_HIT': [ASYNC],
    'TCP_ASYNC_MISS': [ASYNC],
    'ERR_CLIENT_ABORT': [CLIENT_ERR],
    'ERR_CONNECT_FAIL': [SERVER_FAIL],
    'ERR_DNS_FAIL': [SERVER_FAIL],
    'ERR_INVAID_REQ': [CLIENT_ERR],
    'ERR_READ_TIMEOUT': [SERVER_FAIL],
    'ERR_PROXY_DENIED': [CLIENT_ERR],
    'ERR_UNKNOWN': [CLIENT_ERR],
}

status_colors = {
     1: (255,255,255,255),
     2: (32,128,32,255),
     3: (32,32,128,255),
     4: (160,160,32,255),
     5: (128,32,32,255),
}

unknown_color = (192,192,192,0)

def main(fh, num_urls=100, ignore_query=True, debug=False):
    from squidpeek_lib.squidlog import AccessParser as SquidAccessParser
    from squidpeek_lib.sparkogram import Sparkogram
    from squidpeek_lib.sparkbar import Sparkbar
    log = SquidAccessParser(fh, debug=debug)
    urls = {}
    hot_urls = CacheDict(urls, max_size=max(2000, 10*num_urls), trim_to=.5)
    first_utime = None
    line = {} # if the log is empty...
    for line in log:
        if first_utime == None: 
            first_utime = line['utime']
        if line['log_tag'][:3] == 'UDP': continue # ignore ICP
        if line['log_tag'][:9] == 'TCP_ASYNC': continue # ignore async
        if line.has_key('extra_0'): # assume that the extra field is an url-encoded list of the Link header values. Not brilliant, but...
            key = parse_link(urllib.unquote(line['extra_0']))
        else:
            key = line['url']
            if ignore_query:
                scheme, authority, path, query, fragment = urlparse.urlsplit(key)
                path = "/".join([seg.split(";",1)[0] for seg in path.split('/')])
                key = urlparse.urlunsplit((scheme, authority, path, '', ''))
        hash_key = hashUrl(key)
        urls[hash_key] = urls.get(hash_key, 0) + 1
        tmp = hot_urls.get(key, {
          'kbytes': Sparkogram(0,256),
          'elapsed': Sparkogram(0,1000),
          'status': {},
          'types': {},
          'query': {},
          })
        if 200 <= line['status'] < 300:
            tmp['kbytes'].append(line['bytes'] / 1024.0)
        try:
            tmp['status'][line['status'] / 100] += 1
        except KeyError:
            tmp['status'][line['status'] / 100] = 1
        try:
            tag_types = log_tags[line['log_tag']]
        except KeyError:
            if debug:
                sys.stderr.write(
                    "Unknown log tag %s (line %s)" % (
                        line['log_tag'], log.num_processed
                ))
            continue
        if MISS in tag_types:
            tmp['elapsed'].append(line['elapsed'])                
        try:
            for tag_type in tag_types:
                try:
                    tmp['types'][tag_type] += 1
                except KeyError:
                    tmp['types'][tag_type] = 1
        except KeyError:
            sys.stderr.write("Warning: unrecognised log tag: %s" % line['log_tag'])
        if ignore_query:
            hash_url = hashUrl(line['url'])[:8]
            try:
                tmp['query'][hash_url] += 1
            except KeyError:
                tmp['query'][hash_url] = 1
        hot_urls[key] = tmp

    # TODO: url diversity

    url_list = hot_urls.keys()
    url_list.sort(lambda a, b, u=urls: cmp(u[hashUrl(b)], u[hashUrl(a)]))
    
    print """
    <html>
      <head>
        <style type="text/css">
            body {
                font-family: sans-serif;
            }
            th {
                text-align: left;
                background-color: 333;
                color: white;
                font-weight: normal;
                padding: 1px 3px;
            }
            td {
                text-align: right;
            }
            td.secondary {
                background-color: #eee;
            } 
            tr:hover td {
                background-color: #ffc;
                color: black;
            }
            table { 
                font-size: 75%%;
            } 
            th a {
                color: white;
                text-decoration: none;
            }
            .key {
                width: 90%%;
                max-width: 800px;
            }
            dt {
                font-weight: bold;
            }
            .bg0 { background-color: #fff; color: #000; }
            .bg1 { background-color: #eee; color: #000; }
            .bg2 { background-color: #ddd; color: #000; }
            .bg3 { background-color: #ccc; color: #000; }
            .bg4 { background-color: #bbb; color: #000; }
            .bg5 { background-color: #aaa; color: #000; }
            .bg6 { background-color: #999; color: #fff; }
            .bg7 { background-color: #888; color: #fff; }
            .bg8 { background-color: #777; color: #fff; }
            .bg9 { background-color: #666; color: #fff; }
            .bg10 { background-color: #555; color: #fff; }
        </style>
        <title>Squidpeek: %s log lines / %s URLs</title>
      </head>
      <body>
        <h1>Squidpeek</h1>
        <ul>
          <li>%s log lines analysed, %i parsing errors</li>
          <li>%i distinct URLs seen, showing top %i</li>
          <li>Start: <strong>%s</strong></li>
          <li>End: <strong>%s</strong></li>
        </ul>
        <p><em><a href="#key">Key</a></em></p>
        <table>
          
    """ % ( log.num_processed,
            len(urls),
            log.num_processed, 
            log.num_error, 
            len(urls),
            num_urls,
            time.ctime(first_utime), 
            time.ctime(line.get('utime', None)), 
          )
    if ignore_query: 
        query_div_hdr = "<th colspan='2'>query diversity</th>"
    else:
        query_div_hdr = ""
    header_line = """\
<tr>
  <th>url</th>
  <th>accesses</th>
  %s
  <th colspan='2'>hits</th>
  <th colspan='2'>misses</th>
  <th colspan='2'>miss msec</th>
  <th colspan='2'>kbytes</th>
  <th>status codes</th>
""" % query_div_hdr

    i = 0
    for url in url_list[:num_urls]:
        hash_url = hashUrl(url)
        if i % 25 == 0:
            print header_line
        i += 1
        access = urls[hash_url]
        types = hot_urls[url]['types']
        # accesses
        print "<tr><th><a href='%s'>%s</a></th><td class='secondary'>%7i</td>" % (url, url[:max_url_len], access)

        # query diversity
        if ignore_query:
            query_set = hot_urls[url]['query'].values()
            query_ttl = float(sum(query_set))
            query_set.sort()
            query_set.reverse()
            q_div = Sparkogram(0, access) # hack, hack, hack
            qn = 1
            for q in query_set:
                for qc in xrange(q):
                    q_div.append(qn)
                qn += 1
            img = q_div.img()
            if img:
                print """\
    <td>%3i</td>
    <td class='secondary'><img src='%s' title='most popular: %4i%% of accesses'/></td>
    """ % (q_div.max_seen, img, (q_div.max_value / float(access) * 100))
            else:
                print "<td></td><td></td>"

        # % hits
        hit_pct = types.get(HIT, 0) / float(access) * 100
        print "<td class='bg%s' title='%s hits'>%2.0f%%</td>" % (int(hit_pct) / 10, types.get(HIT, 0), hit_pct)
        # hits
        hits = Sparkbar()
        stale_hit = types.get(STALE_HIT, 0)
        negative_hit = types.get(NEGATIVE_HIT, 0)
        memory_hit = types.get(MEMORY_HIT, 0)
        disk_hit = types.get(HIT, 0) - stale_hit - negative_hit - memory_hit
        if negative_hit:
            hits.append(negative_hit, "negative hit", (128,32,32,255))
        if disk_hit:
            hits.append(disk_hit, "disk hit", (192,192,192,0))
        if stale_hit:
            hits.append(stale_hit, "stale hit", (160,160,32,255))
        if memory_hit:
            hits.append(memory_hit, "memory hit", (32,128,32,255))
        print "<td class='secondary'>%s</td>" % hits.img()

        # % misses
        miss_pct = types.get(MISS, 0) / float(access) * 100
        print "<td class='bg%s' title='%s misses'>%2.0f%%</td>" % (int(miss_pct) / 10, types.get(MISS, 0), miss_pct)
        # misses
        misses = Sparkbar()
        no_cache = types.get(CLIENT_NOCACHE, 0)
        validate_yes = types.get(SERVER_VALIDATE_YES, 0)
        validate_no = types.get(SERVER_VALIDATE, 0) - validate_yes
        no_validate = types.get(MISS, 0) - types.get(SERVER_VALIDATE, 0)
        if no_cache:
            misses.append(types.get(CLIENT_NOCACHE, 0), "client no-cache", (128,32,32,255))
        if no_validate:
            misses.append(no_validate, "no validator", (192,192,192,0))
        if validate_no:
            misses.append(validate_no, "validate unsuccessful", (160,160,32,255))
        if validate_yes:
            misses.append(validate_yes, "validate successful", (32,32,128,255))
        print "<td class='secondary'>%s</td>" % misses.img()

        # elapsed miss times
        img = hot_urls[url]['elapsed'].img()
        if img:
            el = hot_urls[url]['elapsed']
            print """\
<td>%4i</td>
<td class='secondary'><img src='%s' title='min: %2.0f msec\nmedian: %2.0f msec\nmax: %2.0f msec'/></td>""" % (
             el.median, img, el.min_seen, el.median, el.max_seen)
        else:
            print "<td></td><td></td>"            

        # bytes
        img = hot_urls[url]['kbytes'].img()
        if img:
            by = hot_urls[url]['kbytes']
            print """\
<td>%3ik</td>
<td class='secondary'><img src='%s' title='min: %2.0fk\nmedian: %2.0fk\nmax: %2.0fk'/></td>""" % (
             by.median, img, by.min_seen, by.median, by.max_seen)
        else:
            print "<td></td><td></td>"

        # status codes
        status_codes = Sparkbar()
        [status_codes.append(hot_urls[url]['status'][s], '%sxx' % s, status_colors.get(s, unknown_color)) for s in hot_urls[url]['status']]
        print "<td class='secondary'>%s</td>" % status_codes.img()

        print "</tr>"
        del hot_urls[url]

    print """
</table>

<div class="key">
<h2 id="key">Key</h2>

<p>Each line in the results indicates the service statistics for one service URL. Most graphics can be 'moused over' to reveal more
detailed statistics for an individual entry.</p>

<h3>accesses</h3>

<p>This column shows how many acccesses that the URL received during the sample period. It does not include ICP or other 
inter-cache traffic, nor does it include 'async' traffic caused by <tt>stale-while-revalidate</tt>.</p>
"""

    if ignore_query:
        print """
<h3>query diversity</h3>

<p>This column shows how many different query arguments were seen for this URL to the left, and a graph of how popular they were 
to the right.</p>

<p>For example, if a URL <tt>http://example.com/foo</tt> has 1000 <tt>accesses</tt>, and a <tt>query diversity</tt> of 250, it means that 250 
different combinations of queries to it were seen. For the purposes of calcuating these metrics, query strings and path parameters are both
considered query arguments, so that both <tt>http://example.com/foo?bar</tt> and <tt>http://example.com/foo;baz=bat</tt> would be collpased 
into the URL above (contributing to the 250 figure).</p>

<p>The graph next to it shows how accesses to the queries are distributed; If there is a high peak on the left and a short tail <img style="background-color: #eee;" src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAUCAYAAAAa2LrXAAABCklEQVR4nGL8//8/g6Ki4v/79+8zMowCkgEAAAD//2IaaAcMdQAAAAD//xoNQAoBAAAA//8aDUAKAQAAAP//Gg1ACgEAAAD//xoNQAoBAAAA//+CByAjI8P/gXTIUAUAAAAA//8aTYEUAgAAAAD//xoNQAoBAAAA//9CCUBFRcXRbEwiAAAAAP//wkiBo4FIGgAAAAD//xrNwhQCAAAAAP//whqAo6mQeAAAAAD//xpNgRQCAAAAAP//whmAo6mQOAAAAAD//8KbAkcDkTAAAAAA//8imIVHAxE/AAAAAP//IqoMHA1E3AAAAAD//2IhViFyII6OXiMAAAAA//8arYUpBAAAAAD//wMAgZ0V1hUT8dEAAAAASUVORK5CYII=' title='most popular:   27% of accesses'/>, it means that
most accesses went to a few query terms, while if there is a low peak and a long tail <img style="background-color: #eee;" src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAUCAYAAAAa2LrXAAABBElEQVR4nGL8//8/g6Ki4v/79+8zMowCkgEAAAD//2IaaAcMdQAAAAD//xoNQAoBAAAA//8aDUAKAQAAAP//Gg1ACgEAAAD//xoNQAoBAAAA//8aDUAKAQAAAP//Gg1ACgEAAAD//2KBMRQVFf/D2KNtQuIBAAAA//8aTYEUAgAAAAD//xoNQAoBAAAA//8aDUAKAQAAAP//whqAyOXhKMAPAAAAAP//YsElQc9AfPDgPoOCgiK9rCMZ4KtUAQAAAP//Gs3CFAIAAAAA//8aDUAKAQAAAP//Gg1ACgEAAAD//xoNQCIAvvoAAAAA//8aDUAKAQAAAP//Gg1ACgEAAAD//wMAXUMU7UJYLdQAAAAASUVORK5CYII=' title='most popular:    4% of accesses'/>, it means that the queries were distributed over a larger
set of request-URIs. Mousing over the graph will show how much of the total accesses went to the most popular query, as a percentage.</p>

<p>In general, a large query diversity means that traffic to a particular service is more difficult to cache; as the query diversity number 
approaches the number of accesses, there is less for the cache to exploit, and the hit rate will go down. However, if a reasonble amount of traffic
goes to the most popular query terms, it is still possible to achieve a decent hit rate.</p>
"""

    print """
<h3>hits</h3>

<p>This column shows the percentage of hits for this URL on the left, and a graph representing their distribution on the right.</p>

<p>In these results, a <em>hit</em> is a response that is served without needing to contact another server. Hits are very fast
and do not cause any load on the systems behind the cache; high hit percentages are desirable.</p>

<dl>
    <dt>negative hits (red)</dt>
        <dd><em>Cached errors</em>. Certain error response status codes are cached, so that the 
        server isn't overwhelmed. A large number indicates that a lot of errrors are coming from your service.</dd>
    <dt>disk hits (grey)</dt>
        <dd><em>Hits served from disk</em>. Fast, but slower than from memory. A large number indicates that
        this service isn't 'hot' enough to be memory cached consistently.</dd>
    <dt>memory hits (green)</dt>
        <dd><em>Hits served from memory</em>. Fastest possible service.</dd>
    <dt>stale hits (yellow)</dt>
        <dd><em>Hits served stale</em>, usually because of mechanisms like <tt>stale-while-revalidate</tt>.
        A small number indicates that these mechanisms are working correctly. A large number indicates that the service
        is taking a long time to revalidate, and/or has a small freshness lifetime.</dd>
</dl>

<h3>misses</h3>

<p>This column shows the percentage of misses for this URL on the left, and a graph representing their distribution on the right.</p>

<p>In these results, a <em>miss</em> is a response that requires some communication with an upstream server -- usually the
origin server, or another cache. Misses are slower and cause load on other systems, and so are less desirable. However, they are
unavoidable (the cache has to fill somehow), and in some situations are desirable because the back-end system has to be contacted.</p>

<dl>
    <dt>client no-cache (yellow)</dt>
        <dd><em>Client asked for a fresh copy</em>, with <tt>Pragma</tt> and/or <tt>Cache-Control</tt> request headers.
        A large number indicates misconfigured and/or aggressive clients.</dd>
    <dt>no validator (grey)</dt>
        <dd><em>No validator present in the cached response, so the cache was forced to fetch a new copy</em>. Validators 
        like <tt>Last-Modified</tt> and <tt>ETag</tt> on responses allow caches to ask of a response has changed, rather
        than getting a whole new one. This can save bandwidth if responses are large, and in some situations can avoid 
        server-side computation. A large number indicates that this feature is not being used.</dd>
    <dt>validate unsuccessful (yellow)</dt>
        <dd><em>Validator present, but validation unsuccessful</em>. A validator was present in the cached response, but  
        the server sent a new copy when contacted. A large number indicates that the server doesn't support validation (even
        though it is sending response headers that can be used as validators), or that the responses are changing quickly on the
        server.</dd>
    <dt>validate successful (green)</dt>
        <dd><em>Validator present, validation successful</em>. A validator was present in the cached response,
        and the server indicated that the same response can be used; a new response was not fetched. A large number indicates
        that the server is sending validators and responding to validating requests.</dd>
</dl>

<h3>miss msec</h3>

<p>This column shows the median miss time on the left, and a one-second wide histogram of miss times on the right, both in 
millisecond units. This indicates how quickly upstream servers are able to send a response.</p>

<p>Note that the times shown are measured from the first request write <tt>read()</tt> to the last response byte <tt>write()</tt>; 
therefore, slow clients can inflate this number if TCP buffers are filled. If the median is '1000', it indicates that the median 
is outside the measured range, and is likely to be greater.</p>

<h3>kbytes</h3>

<p>This column shows the median size (in kilobytes) of successful (2xx) responses served to clients, as well as a 256k-wide 
histogram of responses sizes on the right.</p>

<p>Note that the sizes shown are actual bytes served, including headers, compression, etc. If the median is '256', it indicates
that the median is at least that amount.</p>

<h3>status codes</h3>

<p>This column shows the distribution of status codes served to clients. They include;</p>

<dl>
    <dt>0xx (grey)</dt>
        <dd><em>No response status code sent</em> -- Usually because the client has disconnected (i.e., aborted before
        any response headers have been sent). Large numbers can indicate client timeouts due to server-side delays.</dd>
    <dt>1xx (white)</dt>
        <dd><em>Informational</em> -- rare HTTP-related messages. Mostly harmless, but should not be seen in large numbers.</dd>
    <dt>2xx (green)</dt>
        <dd><em>Success</em> -- normal, successful responses.</dd>
    <dt>3xx (blue)</dt>
        <dd><em>Redirects, etc.</em> -- redirections to other URLs, <tt>300 Multiple Choices</tt> and <tt>304 Not Modified</tt>
        responses. Large numbers usually indicate either redirections or 304's due to client-initiated validation (see <em>misses</em>).</dd>
    <dt>4xx (yellow)</dt>
        <dd><em>Client errors</em> -- problems with the request; e.g., <tt>401 Not Authorised</tt>, 
        <tt>403 Forbidden</tt>, <tt>404 Not Found</tt>. A large number indicates that clients are making bad requests often.</dd>
    <dt>5xx (red)</dt>
       <dd><em>Server errors</em> -- problems on the origin server and/or upstream proxies. 
       A large number indicates that there are frequent upstream failures.</dd>
</dl>
</div>
</body></html>"""

def hashUrl(url):
    return hashlib.md5(url).digest()


TOKEN = r'(?:[^\(\)<>@,;:\\"/\[\]\?={} \t]+?)'
QUOTED_STRING = r'(?:"(?:\\"|[^"])*")'
PARAMETER = r'(?:%(TOKEN)s(?:=(?:%(TOKEN)s|%(QUOTED_STRING)s))?)' % locals()
LINK = r'<[^>]*>\s*(?:;\s*%(PARAMETER)s?\s*)*' % locals()
COMMA = r'(?:\s*(?:,\s*)+)'
LINK_SPLIT = r'%s(?=%s|\s*$)' % (LINK, COMMA)
link_splitter = re.compile(LINK_SPLIT)
def _splitstring(instr, item, split):
    if not instr: 
        return []
    return [ h.strip() for h in re.findall(r'%s(?=%s|\s*$)' % (item, split), instr)]
def _unquotestring(instr):
    if instr[0] == instr[-1] == '"':
        instr = instr[1:-1]
        instr = re.sub(r'\\(.)', r'\1', instr)
    return instr
def parse_link(instr):
    out = {}
    if not instr:
        return out
    for link in [h.strip() for h in link_splitter.findall(instr)]:
        url, params = link.split(">", 1)
        url = url[1:]
        param_dict = {}
        for param in _splitstring(params, PARAMETER, "\s*;\s*"):
            try:
                a, v = param.split("=", 1)
                param_dict[a.lower()] = _unquotestring(v)
            except ValueError:
                param_dict[param.lower()] = None
        out[url] = param_dict
    return out


# freaking RHL doesn't do Python greater than 2.3, so we
# have to do some of it ourselves. Hmph.

from itertools import islice, repeat, count, imap, izip 
from heapq import heapify, heappop

def tee(iterable):
    def gen(next, data={}, cnt=[0]):
        for i in count():
            if i == cnt[0]:
                item = data[i] = next()
                cnt[0] += 1
            else:
                item = data.pop(i)
            yield item
    it = iter(iterable)
    return (gen(it.next), gen(it.next))

def nsmallest(n, iterable, key=None):
    in1, in2 = tee(iterable)
    it = izip(imap(key, in1), count(), in2)                 # decorate
    h = list(it)
    heapify(h)
    result = map(heappop, repeat(h, min(n, len(h))))
#    return map(itemgetter(2), result)                       # undecorate
    return [x[2] for x in result]

class CacheDict(UserDict):
    def __init__(self, urls, max_size=1000, trim_to=.8, **args):
        UserDict.__init__(self, **args)
        self.urls = urls
        self.max_size = max_size
        self.trim_size = max_size * trim_to

    def __getitem__(self, key):
        return self.data[key][0]
        
    def __setitem__(self, key, value):
        self.data[key] = (value, len(self.data))
        if len(self.data) > self.max_size:
            self.trim()

    def trim(self):
        expired = nsmallest(self.max_size - int(self.trim_size), self.data, self.getkey)
        for key in expired:
            del self.data[key]

    def getkey(self, key):
        return self.urls[hashUrl(key)]

def usage():
    print """\
Usage: %s [-n num] [-q] logfile 
          -d      Debug parse errors
          -n num  Number of URLs to report (default: 100)
          -q      Use the query string as part of the URI
         logfile  Squid access log, or '-' for STDIN
""" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    import getopt
    opts, args = getopt.getopt(sys.argv[1:], "dqn:")
    opts = dict(opts)
    try:
        fh = open(args[0])
    except IndexError:
        usage()
    except IOError, msg:
        if args[0] == '-':
            fh = sys.stdin
        else:
            sys.stderr.write("IO Error: %s\n" % msg)
            sys.exit(1)
    if opts.has_key('-d'):
        debug = True
    else:
        debug = False
    if opts.has_key('-n'):
        num_urls = int(opts['-n'])
    else:
        num_urls = 100
    if opts.has_key('-q'):
        ignore_query = False
    else:
        ignore_query = True
    try:
        main(fh, num_urls, ignore_query, debug)
    except KeyboardInterrupt:
        sys.exit(0)