# -*- coding: utf-8 -*-

import re
import os.path
import sys
import setuptools
try:
    from setuptools import setup
    extra_kwargs = {'test_suite': 'cssselect.tests'}
except ImportError:
    from distutils.core import setup
    extra_kwargs = {}

INSTALL_REQUIRES = []
EXTRAS_REQUIRE = {}

if int(setuptools.__version__.split(".", 1)[0]) < 18:
    if sys.version_info[0:2] < (3, 0):
        INSTALL_REQUIRES.append("functools32")
else:
    EXTRAS_REQUIRE[":python_version<'3.0'"] = ["functools32"]

ROOT = os.path.dirname(__file__)
README = open(os.path.join(ROOT, 'README.rst')).read()
INIT_PY = open(os.path.join(ROOT, 'cssselect', '__init__.py')).read()
VERSION = re.search("VERSION = '([^']+)'", INIT_PY).group(1)


setup(
    name='cssselect',
    version=VERSION,
    author='Ian Bicking',
    author_email='ianb@colorstudy.com',
    maintainer='Paul Tremberth',
    maintainer_email='paul.tremberth@gmail.com',
    description=
        'cssselect parses CSS3 Selectors and translates them to XPath 1.0',
    long_description=README,
    url='https://github.com/scrapy/cssselect',
    license='BSD',
    packages=['cssselect'],
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    **extra_kwargs
)
