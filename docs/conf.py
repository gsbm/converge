# converge documentation build configuration
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

# Add package root so autodoc can import converge
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

project = "converge"
copyright = "gsbm"  # noqa: A001
author = "gsbm"
release = "0.1.0"
version = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
]

# MyST: use Markdown for source files
myst_enable_extensions = ["deflist", "tasklist", "colon_fence"]
myst_heading_anchors = 2

# Napoleon: Google/NumPy docstrings (matches codebase)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Autodoc
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}
autosummary_generate = True

# Intersphinx: link to Python and key dependencies
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**/__pycache__"]
root_doc = "index"
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}

html_theme = "shibuya"
html_static_path = ["_static"]
html_title = "converge"
html_short_title = "converge"

# Shibuya: use default layout (left + right sidebars) and global TOC options
html_theme_options = {
    "page_layout": "default",
    "globaltoc_expand_depth": 2,
    "toctree_collapse": False,
    "toctree_maxdepth": 4,
    "accent_color": "bronze",
    "github_url": "https://github.com/gsbm/converge",
}
