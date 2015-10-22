# Package information for PYPI.
__name__ = 'nuclai'
__author__ = 'alexjc'
__version__ = '0.1'

# Check version numbers.
import sys
ver = sys.version_info
assert ver.major == 3 and ver.minor >= 4, "Unsupported Python version."

# Use colored console output.
try:
    import colorama; colorama.init(); del colorama
except ImportError:
    pass

# Call the main entry point.
def run():
    from .__main__ import main
    sys.exit(main(sys.argv))
