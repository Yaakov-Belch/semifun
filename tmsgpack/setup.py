from setuptools import setup, find_packages
from Cython.Build import cythonize
import glob
import os
import sys

sys.path.insert(0, os.getcwd())
from build_pyx import PYX_PATH, write_pyx

write_pyx(PYX_PATH)

pyx_files = glob.glob("tmsgpack/*.pyx")

setup(
    name="tmsgpack",
    packages=find_packages(),
    ext_modules=cythonize(
        pyx_files,
        compiler_directives={
            'language_level': 3,
            'boundscheck': True,
            'wraparound': False,
            'cdivision': True,
        }
    )
)
