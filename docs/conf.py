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
import os
import sys

sys.path.insert(0, os.path.abspath(".."))
import datetime
from pathlib import Path

import pkg_resources
from changelogd import changelogd

ROOT_PATH = Path(__file__).parents[1]

changelogd.release(partial=True, output="history.rst", config=ROOT_PATH / "changelog.d")

# -- Project information -----------------------------------------------------

project = "pytest-subprocess"
copyright = f"2019-{datetime.datetime.now().year}, Andrzej Klajnert"
author = "Andrzej Klajnert"

# The full version, including alpha/beta/rc tags
release = pkg_resources.get_distribution("pip").version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "sphinxcontrib.napoleon",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
]
typehints_fully_qualified = False
always_document_param_types = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_title = "pytest-subprocess"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]
