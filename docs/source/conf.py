# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath("_ext"))
os.environ["DJANGO_SETTINGS_MODULE"] = "moo.settings.local"

import django  # pylint: disable=wrong-import-position

django.setup()

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "django-moo"
copyright = "2024, Phil Christensen"  # pylint: disable=redefined-builtin
author = "Phil Christensen"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_rtd_theme",
    "sphinx_autodoc_typehints",
    "verb_autodoc",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

templates_path = ["_templates"]
exclude_patterns: list[str] = []

autosummary_generate = True
autodoc_mock_imports = ["moo.bootstrap.default", "moo.bootstrap.test"]
autodoc_default_options = {
    "exclude-members": "connection_requested,tap_requested,tun_requested,unix_connection_requested",
}

intersphinx_mapping = {
    "django": ("https://docs.djangoproject.com/en/stable/", None),
}

# We recommend adding the following config value.
# Sphinx defaults to automatically resolve *unresolved* labels using all your Intersphinx mappings.
# This behavior has unintended side-effects, namely that documentations local references can
# suddenly resolve to an external location.
# See also:
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#confval-intersphinx_disabled_reftypes
intersphinx_disabled_reftypes = ["*"]

# Suppress unresolvable forward references in asyncssh's own type annotations.
# NOTE: sphinx_autodoc_typehints emits unresolvable-forward-reference warnings
# for asyncssh's SSHReader type (used in inherited SSHServer methods). These
# are upstream asyncssh annotations and cannot be suppressed via suppress_warnings
# because they use the Python logging system directly. Ignored for now.

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_css_files = [
    "css/custom.css",
]
