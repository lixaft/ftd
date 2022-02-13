# pylint: disable=invalid-name
"""Configuration file for the Sphinx documentation builder.

This file does only contain a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""
import importlib
import os
import sys

# Path setup
path_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
path_docs = os.path.join(path_root, "docs")
path_src = os.path.join(path_root, "src")
sys.path.append(path_src)

ftd = importlib.import_module("ftd")

# Project information
project = "ftd"
author = "Fabien Taxil"
project_copyright = "2021, " + author
version = ftd.__version__

# General configuration
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx_copybutton",
    "autodocsumm",
    "myst_parser",
    "sphinx_panels",
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
needs_sphinx = "4.0"
needs_extensions = {}
add_function_parentheses = True
add_module_names = False
language = None

# Options for HTML output
html_theme = "furo"
html_theme_options = {
    # "light_logo": "",
    # "dark_logo": "",
}
html_title = "ftd"
html_short_title = "ftd"
html_static_path = ["_static"]
# html_favicon = ""
html_show_sourcelink = True
htmlhelp_basename = "ftddoc"
html_css_files = [
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"
]

# Extension configuration
napoleon_use_admonition_for_examples = True
autodoc_mock_imports = ["maya"]
autodoc_default_options = {
    "show-inheritance": True,
    "autosummary": True,
    "members": True,
}
autodoc_member_order = "alphabetical"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
autosummary_generate = True


def setup(app):
    """Setup sphinx application."""
    app.add_css_file("css/style.css")
    app.connect("builder-inited", _generate_stub_pages)
    app.connect("autodoc-process-docstring", _process_docstring)


def _generate_stub_pages(app):
    # pylint: disable=unused-argument
    """Generate documentation stub pages."""
    return


def _process_docstring(app, what, name, obj, options, lines):
    # pylint: disable=unused-argument
    """Customize the way that sphinx parse the docstrings."""
    new_lines = []

    for line in lines:

        if line == "Schema:":
            line = [".. code-block::", ""]

        elif line == ".. admonition:: Examples":
            line = [
                ".. dropdown:: :fa:`code` Examples",
                "   :animate: fade-in",
            ]

        if isinstance(line, list):
            new_lines.extend(line)
        else:
            new_lines.append(line)

    lines[:] = new_lines[:]
