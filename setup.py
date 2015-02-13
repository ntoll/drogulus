#!/usr/bin/env python
from setuptools import setup
from drogulus.version import get_version

with open('README.rst') as f:
    readme = f.read()
with open('CHANGES.rst') as f:
    changes = f.read()

setup(
    name='drogulus',
    version=get_version(),
    description=' '.join(['A peer-to-peer data store built for simplicity,'
                         'security, openness and fun.']),
    long_description=readme + '\n\n' + changes,
    author='Nicholas H.Tollervey',
    author_email='ntoll@ntoll.org',
    url='http://drogul.us/',
    package_dir={'drogulus': 'drogulus'},
    package_data={'': ['ACCORD', 'AUTHORS', 'README.rst', 'CHANGES.rst',
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
    install_requires=['aiohttp', 'rsa', 'cliff', 'pyscrypt'],
    entry_points={
        'console_scripts': ['drogulus=drogulus.drogulus:main'],
        'drogulus.commands': [
            'keygen = drogulus.commands.keygen:KeyGen',
            'whoami = drogulus.commands.whoami:WhoAmI',
            'start = drogulus.commands.start:Start',
        ],
    }
)
