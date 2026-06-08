# SPDX-License-Identifier: GPL-2.0+
"""Sphinx configuration for the patman documentation."""

import pathlib
import tomllib

_pyproject = pathlib.Path(__file__).resolve().parent.parent / 'pyproject.toml'
with open(_pyproject, 'rb') as _fd:
    _meta = tomllib.load(_fd)['project']

project = 'Patman'
author = 'Simon Glass and contributors'
copyright = '2011-2026, Simon Glass and contributors'
release = _meta['version']
version = release

extensions = []
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = []
