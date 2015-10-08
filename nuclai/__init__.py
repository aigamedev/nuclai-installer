__name__ = 'nuclai'
__author__ = 'alexjc'
__version__ = '0.1'

import sys
from .main import main

def run():
    sys.exit(main(sys.argv))

