#!/usr/bin/env python
"""setup.py for the psp package"""

from distutils.core import setup
from os.path import dirname, join


def read(path):
    with open(join(dirname(__file__), path)) as fp:
        return fp.read()

# https://packaging.python.org/en/latest/guides/single-sourcing-package-version/
def get_version(path):
    for line in read(path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    name='psp',
    version=get_version('psp/__init__.py'),
    description='A program for backing up entries in Perspective <3',
    long_description=read('README.md'),
    author='rapidcow',
    author_email='thegentlecow@gmail.com',
    packages=['psp', 'psp.processors', 'psp.extensions'],
)
