# sphinx conf.py
import re
import sphinx_rtd_theme

project = u'Validate your idea'
copyright = u'2014, Lukas Ender'

master_doc = 'index'
source_suffix = '.txt'

VERSIONFILE = open("../src/timpe/app/__init__.py").read()
VERSION_REGEX = r'^__version__ = [\'"]([^\'"]*)[\'"]$'
M = re.search(VERSION_REGEX, VERSIONFILE, re.M)
VERSION = M.group(1)

version = VERSION
release = VERSION

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
