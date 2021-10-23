import os
import sys
from os import path

import numpy as np
from Cython.Build import cythonize
from setuptools import Extension, find_packages, setup

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

if sys.platform == "win32":
    extra_compile_args = ["/openmp", "/O2"]
    extra_link_args = ["/openmp"]
else:
    extra_compile_args = [
        "-fopenmp",
        "-O3",
        "-ffast-math",
        "--std=c++17",
    ]
    extra_link_args = ["-fopenmp"]

extension_args = dict(
    include_dirs=[np.get_include()],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
    language="c++",
)
ext_modules = [
    Extension(
        name="tectosaur2._local_qbx",
        sources=["tectosaur2/_local_qbx.pyx"],
        **extension_args,
    ),
]

setup(
    name="tectosaur2",
    use_scm_version={"version_scheme": "post-release"},
    setup_requires=["setuptools_scm"],
    description="Boundary integral tools and tutorials, focused on earthquakes.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tbenthompson/tectosaur2",
    author="T. Ben Thompson",
    author_email="t.ben.thompson@gmail.com",
    license="MIT",
    classifiers=[  # Optional
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_packages(),
    install_requires=[],
    entry_points=None,
    ext_modules=cythonize(ext_modules, annotate=False),
    zip_safe=False,
)