# pylint: disable=invalid-name, unused-argument
"""Configuration file for the Sphinx documentation builder.

This file does only contain a selection of the most common options. For a
full list see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""
import importlib
import os
import sys

# Path setup.
root_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
docs_path = os.path.join(root_path, "docs")
src_path = os.path.join(root_path, "src")
ext_path = os.path.join(docs_path, "ext")
sys.path.append(src_path)
sys.path.append(ext_path)

# Import package.
ftd = importlib.import_module("ftd")

# Project information.
project = "ftd"
author = "Fabien Taxil"
project_copyright = "2021, " + author
version = ftd.__version__

# General configuration.
extensions = [
    "sphinx.ext.todo",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.inheritance_diagram",
    "sphinx_copybutton",
    "autodocsumm",
    "myst_parser",
    "sphinx_panels",
    "apigen",
]
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
needs_sphinx = "4.0"
needs_extensions = {}
add_function_parentheses = True
add_module_names = False
language = None

# Options for HTML output.
html_theme = "furo"
html_title = "ftd"
html_short_title = "ftd"
html_static_path = ["_static"]
html_show_sourcelink = True
htmlhelp_basename = "ftddoc"

# Extension configuration.
napoleon_use_admonition_for_examples = True
todo_include_todos = True
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
autodoc_mock_imports = ["maya"]
autodoc_default_options = {"show-inheritance": True}
apigen_config = {"ftd": None}


def process_docstring(app, what, name, obj, options, lines):
    """Customize the way that sphinx parse the docstrings."""
    old_lines = list(lines)
    lines[:] = []
    for line in old_lines:

        # Replace the schema by a code block directive.
        if line == "Schema:":
            line = [".. code-block::", ""]

        # Replace all example admonitions with sphinx-panel dropdowns (examples
        # must be converted to admonitions first using the setting:
        # `napoleon_use_admonition_for_examples=True`)
        elif line == ".. admonition:: Examples":
            line = line.replace("admonition", "dropdown")

        # Add the new line(s).
        if isinstance(line, list):
            lines.extend(line)
        else:
            lines.append(line)


def setup(app):
    """Setup sphinx application."""
    app.add_css_file("css/style.css")
    app.connect("autodoc-process-docstring", process_docstring)
