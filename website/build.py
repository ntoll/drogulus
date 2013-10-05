#!/usr/bin/env python
"""
Uses Jinja2 to generate the static drogul.us website.
"""
import os, sys
from jinja2 import Template, Environment, FileSystemLoader

path = os.path.abspath(os.path.dirname(sys.argv[0]))

env = Environment(loader=FileSystemLoader(os.path.join(path, 'templates')))

rss = Template(u"""<rss version="2.0">
<channel>
    <title>The drogulus - a programmable p2p data store</title>
    <link>http://drogul.us/news</link>
    <description></description>
    <image>
        <url>http://drogul.us/images/logo.png</url>
        <link>http://drogul.us/</link>
    </image>
    {% for item in items %}
    <item>
        <title>{{ item.title }}</title>
        <link>http://drogul.us/news#{{ item.slug }}</link>
        <description>{{ item.content }}</description>
        <pubDate>{{ item.pub }}</pubDate>
    </item>
    {% endfor %}
</channel>
</rss>
""")

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

# Generate the homepage and RSS feed. Use only the most recent three articles.
"""
for article in articles[:3]:
    filename = article['slug'] + '.html'
    raw = open('site/templates/articles/%s' % filename)
    raw_content = raw.readlines()
    content = ''.join(raw_content[3:-1])
    title = '<h1><a href="/article/%s">%s</a></h1>' % (article['slug'], article['title'])
    content = title + content
    article['content'] = content
    date = datetime.strptime(article['date'], '%Y-%m-%d %H:%M:%S')
    pub = date.strftime('%a, %d %B %Y %H:%M:%S GMT')
    article['pub'] = pub
    rss_list.append(article)
    home.append(content)"""
