#!/usr/bin/env python

"""
sparkogram.py - Sparkline histogram generator

This is quick and dirty. Based on Joe Gregorio's sparkline thoughts;
  <http://bitworking.org/news/Sparklines_in_data_URIs_in_Python>.
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

__version__ = '0.23'

import sys
import base64
import StringIO
from PIL import Image, ImageDraw # <http://www.pythonware.com/products/pil/>

class Sparkogram(object):
    """
    Given a data set, return a IMG tag suitable for insertion into HTML.
    The image will be a histogram of the data, with the median value 
    highlighted.
    
    The ends of the histogram can be overridden with "start" and "finish" (which
    default to the min and the max of the data); if any values fall outside of 
    these, the ends will represent these values, and be highlighted in red.
    
    data: list of numbers (int or float)
    width: width of sparkline, in pixels
    height: height of sparkline, in pixels
    start: left-most value
    finish: right-most value
    color: color of the graph
    bg_color: background color
    median_color: color that median value will be highlighted with
    
    Note that colors can be specified in a variety of ways, depending on
    the version of PIL that you have installed. See:
      <http://www.pythonware.com/library/pil/handbook/imagedraw.htm>
    """
    __slots__ = ['min', 'max', 'num_buckets', 'bucket_width', 'buckets', '_over', '_under', 'min_seen', 'max_seen', 'median', 'max_value']

    def __init__(self, min, max, num_buckets=None):
        self.min = min
        self.max = max
        if num_buckets is None:
            self.num_buckets = max - min
        else:
            self.num_buckets = num_buckets
        self.bucket_width = (max - min) / float(self.num_buckets)
        if self.bucket_width == 0:
            self.bucket_width = 1 # hack for single-value datasets
        self.buckets = {}
        self._over = 0
        self._under = 0
        self.min_seen = None
        self.max_seen = None
        self.median = None
        self.max_value = None

    def append(self, data):
        if self.min_seen is None or data < self.min_seen: self.min_seen = data
        if self.max_seen is None or data > self.max_seen: self.max_seen = data
        if data > self.max:
            self._over += 1
            return
        if data < self.min:
            self._under += 1
            return
        i = data - self.min
        try:
            self.buckets[i - (i % self.bucket_width)] += 1
        except KeyError:
            self.buckets[i - (i % self.bucket_width)] = 1

    def img(self, width=80, height=20, color=(32,32,32,255), 
            bg_color=(255,255,255,0), median_color=(0,0,255,255)):
        bl = self.buckets.keys()
        bl.sort()
        dataset = []
        [dataset.extend([b] * self.buckets[b]) for b in bl if self.buckets[b]]

        # figure out the image buckets
        num_img_buckets = width - 2
        img_bucket_width = (self.max - self.min) / float(num_img_buckets)
        if img_bucket_width == 0: # hack for single-value datasets
            img_bucket_width = 1.0
        img_buckets = dict([(n * img_bucket_width, 0) for n in xrange(num_img_buckets + 1)])
        for item in dataset:
            try:
                img_buckets[item - (item % img_bucket_width)] += 1
            except KeyError:
                k = img_buckets.keys()
                k.sort()
                print item, img_bucket_width, k
                raise KeyError
        img_bl = img_buckets.keys()
        img_bl.sort()

        # calculate median
        dataset.extend([self.min] * self._under)
        dataset.extend([self.max] * self._over)
        dataset.sort()
        if len(dataset) == 0: return ""
        median = dataset[int(len(dataset) / 2)]
        try:
            median_x = img_bl.index((median) - ((median) % img_bucket_width))
        except ValueError: # median is in the min or max
            median_x = None
        self.max_value = float(max(img_buckets.values() + [self._over, self._under]))
        self.median = median + self.min

        height -= 1
        coords = [(i + 1, height - (height * (img_buckets[img_bl[i]] / self.max_value)))
                  for i in xrange(num_img_buckets)]
        im = Image.new("RGBA", (width, height + 1), bg_color)
        draw = ImageDraw.Draw(im)
        if self._under > 0:
            draw.line([(0, height), (0, height - (height * max(self._under / self.max_value), 1))], fill=(255,0,0,255))
        for x, y in coords:
            if y != height:
                this_color = (x == median_x) and median_color or color
                draw.line([(x, height), (x, y)], fill=this_color)
        if self._over > 0:
            draw.line([(width - 1, height), (width -1, height - (height * max(self._over / self.max_value, 1)))], fill=(255,0,0,255))
        del draw

        f = StringIO.StringIO()
        im.save(f, "PNG")
        return "data:image/png;base64,%s" % base64.encodestring(f.getvalue()).replace('\n', '')

def test():
    sp = Sparkogram(0, 1000)
    [sp.append(i) for i in [1,1,1,0,0,1,1,45,45,45,4,4,1,0,0,45,101,5000,5000,45,54,55,55,55,55]]
    print sp.img()
    
if __name__ == '__main__':
    test()