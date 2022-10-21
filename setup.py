# -*- coding: utf-8 -*-

import re
import os.path

try:
    from setuptools import setup

    extra_kwargs = {"test_suite": "cssselect.tests"}
except ImportError:
    from distutils.core import setup

    extra_kwargs = {}


ROOT = os.path.dirname(__file__)
with open(os.path.join(ROOT, "README.rst")) as readme_file:
    README = readme_file.read()
with open(os.path.join(ROOT, "cssselect", "__init__.py")) as init_file:
    INIT_PY = init_file.read()
VERSION = re.search('VERSION = "([^"]+)"', INIT_PY).group(1)


setup(
    name="cssselect",
    version=VERSION,
    author="Ian Bicking",
    author_email="ianb@colorstudy.com",
    maintainer="Paul Tremberth",
    maintainer_email="paul.tremberth@gmail.com",
    description="cssselect parses CSS3 Selectors and translates them to XPath 1.0",
    long_description=README,
    url="https://github.com/scrapy/cssselect",
    license="BSD",
    packages=["cssselect"],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    **extra_kwargs,
)
