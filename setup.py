#!/usr/bin/env python
from distutils.core import setup
from drogulus.version import get_version

setup(
    name='drogulus',
    version=get_version(),
    description='A federated, decentralised, openly writable yet easily' +
        ' searchable information store and computation platform.',
    long_description=open('README.rst').read(),
    author='Nicholas H.Tollervey',
    author_email='ntoll@ntoll.org',
    url='http://packages.python.org/Drogulus',
    packages=['drogulus', 'drogulus/dht'],
    scripts=['bin/drogd'],
    license='GNU AGPLv3',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Topic :: Communications',
        'Topic :: Database',
        'Topic :: Internet',
        'Topic :: Security',
        'Topic :: System :: Distributed Computing',
    ]
)
