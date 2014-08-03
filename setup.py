#!/usr/bin/env python
from setuptools import setup, find_packages
from drogulus.version import get_version

setup(
    name='drogulus',
    version=get_version(),
    description='A peer-to-peer, decentralised, openly writable information' +
                ' store.',
    long_description=open('README.rst').read(),
    author=open('AUTHORS').read(),
    author_email='ntoll@ntoll.org',
    url='http://drogul.us/',
    package_dir={'': 'drogulus'},
    packages=find_packages('drogulus'),
    license='Public Domain',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: Public Domain',
        'Topic :: Communications',
        'Topic :: Internet',
        'Topic :: System :: Distributed Computing',
    ],
    install_requires=['pycrypto', ]
)
