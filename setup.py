#!/usr/bin/env python
from setuptools import setup, find_packages
from drogulus.version import get_version

setup(
    name='drogulus',
    version=get_version(),
    description='A federated, decentralised, openly writable information' +
                ' store and computation platform.',
    long_description=open('README.rst').read(),
    author='Nicholas H.Tollervey',
    author_email='ntoll@ntoll.org',
    url='http://packages.python.org/drogulus',
    package_dir={'': 'drogulus'},
    packages=find_packages('drogulus'),
    scripts=['bin/drogd'],
    license='GNU AGPLv3',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Topic :: Communications',
        'Topic :: Database',
        'Topic :: Internet',
        'Topic :: Security',
        'Topic :: System :: Distributed Computing',
    ],
    install_requires=['pycrypto', 'twisted', 'msgpack-python']
)
