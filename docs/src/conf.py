# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

from multiproject.utils import get_project

multiproject_projects = {
    'en': {
        'path': '.',
        'use_config_file': False,
    },
    'zh_CN': {
        'path': '.',
        'use_config_file': False,
    },
}

current_project = get_project(multiproject_projects)

# -- Project information -----------------------------------------------------

project = {
    'en': 'The Perspective Library',
    'zh_CN': 'Perspective 库',
}[current_project]
copyright = '2022, rapidcow'
author = 'rapidcow'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.intersphinx',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'multiproject',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'furo'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'css/stylesheet.css',
]


# -- Internationalization ----------------------------------------------------

language = current_project
locale_dirs = ['locale/']
gettext_compact = True


# Numbered figures
numfig = True
numfig_format = {
    'figure': 'Figure %s',
    'table': 'Table %s',
    'code-block': 'Listing %s',
}

# By default, highlight as Python 3.
highlight_language = 'python3'


# -- Options for doctest (sphinx.ext.doctest) --------------------------------
# basicproc.py isn't a part of the Perspective library.  But I don't
# feel like removing it anyway, so...
doctest_global_setup = """\
try:
    import basicproc
except ImportError:
    basicproc = None
"""
# We require exception messages to be exact!
# (Override the flags so that IGNORE_EXCEPTION_DETAIL is unset)
import doctest
doctest_default_flags = doctest.ELLIPSIS | doctest.DONT_ACCEPT_TRUE_FOR_1


# -- Options for sphinx.ext.intersphinx --------------------------------------
#
# Define a mapping for external documentation, which will be looked up in
# when a reference (like :func:`io.open`) is undefined.  The following links
# to Python's official documentation at docs.python.org.
#
# https://www.sphinx-doc.org/en/master/usage/quickstart.html#intersphinx
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#confval-intersphinx_mapping
#
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}
### infinite timeout! yippee!!
# intersphinx_timeout = 30
