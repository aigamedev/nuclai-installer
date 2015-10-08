# Package information for PYPI.
__name__ = 'nuclai'
__author__ = 'alexjc'
__version__ = '0.1'

# Use colored console output.
try:
    import colorama; colorama.init(); del colorama
except ImportError:
    pass

# Call the main entry point.
import sys
from .main import main

def run():
    sys.exit(main(sys.argv))
