#!/usr/bin/env python
"""
Uses Jinja2 to generate the static drogul.us website.
"""
import os
import sys
from jinja2 import Environment, FileSystemLoader

path = os.path.abspath(os.path.dirname(sys.argv[0]))

env = Environment(loader=FileSystemLoader(os.path.join(path, 'templates')))

pages = ['code', 'contact', 'why', 'what', 'how', 'index']

home = []
rss_list = []
article_list = []

for page in pages:
    filename = page + '.html'
    template = env.get_template(filename)
    outfile = open(os.path.join(path, 'site', filename), 'wb')
    x = template.render()
    outfile.write(x)
    outfile.close()
