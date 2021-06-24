===================================
cssselect: CSS Selectors for Python
===================================

.. image:: https://img.shields.io/pypi/v/cssselect.svg
   :target: https://pypi.python.org/pypi/cssselect
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/cssselect.svg
   :target: https://pypi.python.org/pypi/cssselect
   :alt: Supported Python Versions

.. image:: https://github.com/scrapy/cssselect/actions/workflows/tests.yml/badge.svg
   :target: https://github.com/scrapy/cssselect/actions/workflows/tests.yml
   :alt: Tests

.. image:: https://img.shields.io/codecov/c/github/scrapy/cssselect/master.svg
   :target: https://codecov.io/github/scrapy/cssselect?branch=master
   :alt: Coverage report

*cssselect* parses `CSS3 Selectors`_ and translate them to `XPath 1.0`_
expressions. Such expressions can be used in lxml_ or another XPath engine
to find the matching elements in an XML or HTML document.

This module used to live inside of lxml as ``lxml.cssselect`` before it was
extracted as a stand-alone project.

.. _CSS3 Selectors: https://www.w3.org/TR/css3-selectors/
.. _XPath 1.0: https://www.w3.org/TR/xpath/
.. _lxml: http://lxml.de/


Quick facts:

* Free software: BSD licensed
* Compatible with Python 3.6+
* Latest documentation `on Read the Docs <https://cssselect.readthedocs.io/>`_
* Source, issues and pull requests `on GitHub
  <https://github.com/scrapy/cssselect>`_
* Releases `on PyPI <http://pypi.python.org/pypi/cssselect>`_
* Install with ``pip install cssselect``
