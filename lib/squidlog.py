#!/usr/bin/env python

'''
Squid Web proxy cache log parsing classes.
'''


# (c) 1998-2007 Copyright Mark Nottingham
# <mnot@pobox.com>
#
# This software may be freely distributed, modified and used, 
# provided that this copyright notice remain intact.
#
# This software is provided 'as is' without warranty of any kind.


# Squid Access Logfile Format
# ---------------------------
#
# Version 1.1 Access log
# 
# timestamp elapsed_time client log_tag/status bytes method URL rfc931 \
# peer_tag/peerhost mimetype
#
# rfc931: identd info, - otherwise
#
#
# Squid Store Logfile Format
# --------------------------
#
# Version 1.1 Store log
#
# time action status datehdr lastmod expires type expect-len/real-len \
# method key
#
#
# for more information about both formats, see the Squid FAQ at
# http://squid.nlanr.net/




__version__ = '2.0'


from string import atoi, atof, split, join, lower
from re import compile
from urllib import unquote
import sys


class AccessParser:
    ''' Splitting Squid Access Logfile Parser '''

    _mime_splitter = compile("\[(.*?)\] \[(.*?)\]")
    _mime_indexer = compile("%0d%0a")
    _mime_hasher = compile("([\w\-_]+):\s*(.*)$")
    _time_headers = ['date', 'last-modified', 'expires']

    def __init__(self, file_descriptor, parse_headers=False, debug=False):
        self._fd = file_descriptor
        self.parse_headers = parse_headers
        self.debug = debug
        self.num_processed = 0
        self.num_error = 0

    def __iter__(self):
        return self
    
    def next(self):
        while 1:     # loop until we find a valid line, or end
            line = self._fd.next()
            self.num_processed += 1
            n = split(line, None)
            try:
                o = {
                    'utime': int(float(n[0])),
                    'elapsed': int(n[1]),
                    'client': n[2],
                    'bytes': int(n[4]),
                    'method': n[5],
                    'url': n[6],
                    'ident': n[7],
                    'mimetype': n[9]
                }
                o['log_tag'], status = split(n[3], '/', 2) 
                o['status'] = int(status)
                o['peer_tag'], o['peerhost'] = split(n[8], '/', 2)
                if len(n) > 10: 
                    if self.parse_headers and n[10][0] == '[':  # mime headers present                
                        o['hdr_request'], o['hdr_response'] = self._parse_mime(" ".join(n[10:]))
                    else: # some other fields; just save them raw in extra...
                        i = 0
                        for field in n[10:]:
                            i += 1
                            o['extra_%s' % i] = field
                return o
            except Exception, why:
                self.num_error = self.num_error + 1
                if self.debug:
                    sys.stderr.write("PARSE ERROR line %s: %s\n" % (
                        self.num_processed, why
                    ))
                continue        

    def _parse_mime(self, raw):
        match = self._mime_splitter.match(raw)
        if not match:
            return {}, {}
        return (    self._process_hdr(match.group(1)), 
                    self._process_hdr(match.group(2))    )


    def _process_hdr(self, raw_header):
        from time import mktime, timezone
        from rfc822 import parsedate
    
        hdrs = {}
        header_list = self._mime_indexer.split(raw_header)
        for header in header_list:
            match = self._mime_hasher.match(header)
            if not match:
                continue

            key = lower(match.group(1))
            value = unquote(match.group(2))

            if key in self._time_headers:
                value = mktime(parsedate(value)) - timezone
            hdrs[key] = value

        return hdrs
            
def test_access():
    log = AccessParser(sys.stdin)
    for line in log:
        print "%s %s %s" % (line['url'], line['status'], line['log_tag'])
    print "lines: %s" % (log.num_processed)
    print "error: %s" % (log.num_error)
        
        
if __name__ == '__main__':
    test_access()



