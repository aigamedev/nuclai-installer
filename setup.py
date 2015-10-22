import os
import sys

from setuptools import setup, find_packages


pwd = os.path.abspath(os.path.dirname(__file__))
sys.path.append(pwd)

try:
    import nuclai
    VERSION = nuclai.__version__
except ImportError as e:
    VERSION = 'N/A'


setup(name='nuclai',
      version=VERSION,
      description='Cross-platform Installer & Runner for nucl.ai tutorials and excercises.',
      author='Alex J. Champandard',
      url='https://github.com/aigamedev/nuclai-installer',
      
      long_description=open(os.path.join(pwd, 'README.rst')).read(),
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3.4',
          'License :: Free For Home Use',
          'Topic :: Scientific/Engineering :: Artificial Intelligence'
      ],
      license='GNU GPLv3',

      scripts=['scripts/nuclai'],
      packages=find_packages(),

      include_package_data=True,
      install_requires=[
            'colorama' if sys.platform == 'win32' else '',
      ])
