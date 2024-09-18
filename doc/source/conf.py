# conf.py

import os
import sys
sys.path.insert(0, os.path.abspath('../..')) 

project = 'pyjevsim'  # 프로젝트 이름
author = 'jaiyun'  # 작성자 이름
release = '0.1.0'  # 프로젝트 버전

extensions = [
    'sphinx.ext.autodoc',      # Python 자동 문서화 기능
    'sphinx.ext.napoleon',     # Google 및 NumPy 스타일의 docstrings 지원
    'sphinx.ext.viewcode',     # 소스코드 링크 추가
    'sphinx.ext.githubpages',  # GitHub Pages 지원
]

# The master toctree document.
master_doc = 'index'
