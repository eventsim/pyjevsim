import os
import re
import sys
from pathlib import Path

from sphinx.application import Sphinx

import os
import sys
sys.path.insert(0, os.path.abspath('../'))  

project = 'pyjevsim' 
author = 'jaiyun'

extensions = [
    'sphinx.ext.autodoc',      
    'sphinx.ext.napoleon',     
    'sphinx.ext.viewcode',     
    'sphinx.ext.githubpages',  
]

pygments_style = "sphinx"
highlight_language = "python3"
html_theme = "furo"

html_theme_options = {
    "navigation_with_keys": True,
    "dark_css_variables": {
        "admonition-title-font-size": "0.95rem",
        "admonition-font-size": "0.92rem",
    },
    "light_css_variables": {
        "admonition-title-font-size": "0.95rem",
        "admonition-font-size": "0.92rem",
    },    
}

