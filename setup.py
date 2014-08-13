#!/usr/bin/env python
from setuptools import setup
from drogulus.version import get_version

with open('README.rst') as f:
    readme = f.read()
with open('HISTORY.rst') as f:
    history = f.read()

setup(
    name='drogulus',
    version=get_version(),
    description=' '.join(['A peer-to-peer data store built for simplicity,'
                         'security, openness and fun.']),
    long_description=readme + '\n\n' + history,
    author='Nicholas H.Tollervey',
    author_email='ntoll@ntoll.org',
    url='http://drogul.us/',
    package_dir={'drogulus': 'drogulus'},
    package_data={'': ['ACCORD', 'AUTHORS', 'README.rst', 'HISTORY.rst',
                       'LICENSE', 'UNLICENSE', 'WAIVER']},
    packages=['drogulus', 'drogulus.contrib', 'drogulus.net',
              'drogulus.commands', 'drogulus.dht'],
    license='Public Domain',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: Public Domain',
        'Programming Language :: Python :: 3.3',
        'Topic :: Communications',
        'Topic :: Internet',
        'Topic :: System :: Distributed Computing',
    ],
    install_requires=['pycrypto', 'cliff'],
    entry_points={
        'console_scripts': ['drogulus=drogulus.drogulus:main'],
        'drogulus.commands': [
            'keygen = drogulus.commands.keygen:KeyGen',
            'whoami = drogulus.commands.whoami:WhoAmI',
            'start = drogulus.commands.start:Start',
        ],
    }
)
