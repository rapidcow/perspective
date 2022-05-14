#!/usr/bin/env python
"""setup.py for the psp package"""

from distutils.core import setup
from os.path import dirname, join


def read(path):
    with open(join(dirname(__file__), path)) as fp:
        return fp.read()


setup(
    name='psp',
    version='0.1.1',
    description='A program for backing up entries in Perspective <3',
    long_description=read('README.md'),
    author='rapidcow',
    author_email='thegentlecow@gmail.com',
    packages=['psp', 'psp.processors', 'psp.extensions'],
)
