import os
import sys
from importlib.metadata import PackageNotFoundError, version

# Require Python 3.8+
if sys.version_info < (3, 8):
    sys.exit("You have an old version of python. Install version 3.8 or higher.")

# Get version
try:
    __version__ = version("cli50")
except PackageNotFoundError:
    __version__ = "UNKNOWN"
