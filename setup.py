#!/usr/bin/env python

from distutils.core import setup
from squidpeek import __version__ as version

setup(
  name = 'squidpeek',
  version = version,
  description = 'Per-URL Squid logfile metrics',
  author = 'Mark Nottingham',
  author_email = 'mnot@mnot.net',
  url = 'http://github.com/mnot/squidpeek/',
  download_url = \
    'http://github.com/mnot/squidpeek/tarball/squidpeek-%s' % version,
  packages = ['squidpeek_lib'],
  package_dir = {'squidpeek_lib': 'lib'},
  scripts = ['squidpeek.py'],
  install_requires = ['PIL > 1.1.4'],
  long_description=open("README.rst").read(),
  classifiers = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Internet :: Proxy Servers',
    'Topic :: Internet :: Log Analysis',
    'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
  ]
)