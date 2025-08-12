import os
import sys

# Ensure imports like 'from legacy_streamlit...' work when executing modules inside the app directory
_PACKAGE_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_PACKAGE_DIR, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
