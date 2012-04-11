"""
Extracted from lxml.tests.common_imports
"""
import re
import sys
import os.path
import unittest
import doctest


def read_file(name, mode='r'):
    f = open(name, mode)
    try:
        data = f.read()
    finally:
        f.close()
    return data


def _get_caller_relative_path(filename, frame_depth=2):
    module = sys.modules[sys._getframe(frame_depth).f_globals['__name__']]
    return os.path.normpath(os.path.join(
            os.path.dirname(getattr(module, '__file__', '')), filename))


if sys.version_info[0] >= 3:
    # Python 3
    from builtins import str as unicode
    def _str(s, encoding="UTF-8"):
        return s
    def _bytes(s, encoding="UTF-8"):
        return s.encode(encoding)
    from io import StringIO, BytesIO as _BytesIO
    def BytesIO(*args):
        if args and isinstance(args[0], str):
            args = (args[0].encode("UTF-8"),)
        return _BytesIO(*args)

    doctest_parser = doctest.DocTestParser()
    _fix_unicode = re.compile(r'(\s+)u(["\'])').sub
    _fix_exceptions = re.compile(r'(.*except [^(]*),\s*(.*:)').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = read_file(filename)
        doctests = _fix_unicode(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1 as \2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))
else:
    # Python 2
    from __builtin__ import unicode
    def _str(s, encoding="UTF-8"):
        return unicode(s, encoding=encoding)
    def _bytes(s, encoding="UTF-8"):
        return s
    from StringIO import StringIO
    BytesIO = StringIO

    doctest_parser = doctest.DocTestParser()
    _fix_traceback = re.compile(r'^(\s*)(?:\w+\.)+(\w*(?:Error|Exception|Invalid):)', re.M).sub
    _fix_exceptions = re.compile(r'(.*except [^(]*)\s+as\s+(.*:)').sub
    _fix_bytes = re.compile(r'(\s+)b(["\'])').sub
    def make_doctest(filename):
        filename = _get_caller_relative_path(filename)
        doctests = read_file(filename)
        doctests = _fix_traceback(r'\1\2', doctests)
        doctests = _fix_exceptions(r'\1, \2', doctests)
        doctests = _fix_bytes(r'\1\2', doctests)
        return doctest.DocTestCase(
            doctest_parser.get_doctest(
                doctests, {}, os.path.basename(filename), filename, 0))
