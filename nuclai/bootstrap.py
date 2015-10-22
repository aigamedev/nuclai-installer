import os
import sys

# Setup the path to known locations of GLFW's DLL on Windows
if 'win32' in sys.platform:
    os.environ['PATH'] += os.pathsep + r'C:\ProgramData\chocolatey\msvc120-64\bin'

# Inject support for local font loading into VisPy.
def _get_vispy_font_filename(face, bold, italic):
    return os.path.join(os.path.dirname(__file__), 'data/questrial.ttf')

# Fonts on Mac OSX.
try:
    from vispy.util.fonts import _quartz
    _quartz._vispy_fonts = ('Questrial',)
    _quartz._get_vispy_font_filename = _get_vispy_font_filename
    del _quartz
except:
    pass

# Fonts on Windows and Linux.
try:
    from vispy.util.fonts import _freetype
    _freetype._vispy_fonts = ('Questrial',)
    _freetype._get_vispy_font_filename = _get_vispy_font_filename
    del _freetype
except:
    pass
