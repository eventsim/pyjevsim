import os
import re
import sys
from pathlib import Path

from sphinx.application import Sphinx

import os
import sys
sys.path.insert(0, os.path.abspath('../../'))  

project = 'pyjevsim' 
author = 'jaiyun'  # 작성자 이름
release = '1.0'  # 프로젝트 버전

extensions = [
    'sphinx.ext.autodoc',      # Python 자동 문서화 기능
    'sphinx.ext.napoleon',     # Google 및 NumPy 스타일의 docstrings 지원
    'sphinx.ext.viewcode',     # 소스코드 링크 추가
    'sphinx.ext.githubpages',  # GitHub Pages 지원
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

