#!/usr/bin/env python

"""
sparkogram.py - Sparkline bar generator
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

__version__ = '0.3'

import sys
import base64
import StringIO
from PIL import Image, ImageDraw # <http://www.pythonware.com/products/pil/>

class Sparkbar(object):
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
    __slots__ = ['data']

    def __init__(self):
        self.data = []
        
    def append(self, num, title, color):
        self.data.append((num, title, color))

    def img(self, width=80, height=20, bg_color=(255,255,255,0)):
        total = float(sum([item[0] for item in self.data]))
        
        data = [(int(i[0] / total * width), i[1], i[2]) for i in self.data]

        im = Image.new("RGBA", (width, height + 1), bg_color)
        draw = ImageDraw.Draw(im)
        left_buf = 0
        for item in data:
            draw.rectangle([(left_buf, 0), (left_buf + item[0], height)], fill=item[2])
            left_buf += item[0]
        del draw

        f = StringIO.StringIO()
        im.save(f, "PNG")
        return """\
<img src="data:image/png;base64,%s" title="%s"/>""" % (
          base64.encodestring(f.getvalue()).replace('\n', ''), 
          "\n".join(["%s: %i" % (i[1], i[0]) for i in self.data])
          )
        del f
        del im

def test():
    sp = Sparkbar()
    sp.append(45,'aaa',(255,0,0,255))
    sp.append(15,'bbbbb b',(0,255,0,255))
    sp.append(100,'c',(0,0,255,255))
    print sp.img()
    
if __name__ == '__main__':
    test()