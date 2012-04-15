"""
    CSS Selectors based on XPath
    ============================

    This module supports selecting XML/HTML elements based on CSS selectors.
    See the `CSSSelector` class for details.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import re
from cssselect.parser import (parse, _unicode, SelectorSyntaxError,
                              ExpressionError)

__all__ = ['SelectorSyntaxError', 'ExpressionError', 'css_to_xpath']


try:
    _basestring = basestring
except NameError:
    # Python 3
    _basestring = str


_el_re = re.compile(r'^\w+\s*$', re.UNICODE)
_id_re = re.compile(r'^(\w*)#(\w+)\s*$', re.UNICODE)
_class_re = re.compile(r'^(\w*)\.(\w+)\s*$', re.UNICODE)

def css_to_xpath(css_expr, prefix='descendant-or-self::'):
    if isinstance(css_expr, _basestring):
        match = _el_re.search(css_expr)
        if match is not None:
            return '%s%s' % (prefix, match.group(0).strip())
        match = _id_re.search(css_expr)
        if match is not None:
            return "%s%s[@id = '%s']" % (
                prefix, match.group(1) or '*', match.group(2))
        match = _class_re.search(css_expr)
        if match is not None:
            return "%s%s[@class and contains(concat(' ', normalize-space(@class), ' '), ' %s ')]" % (
                prefix, match.group(1) or '*', match.group(2))
        css_expr = parse(css_expr)
    expr = css_expr.xpath()
    assert expr is not None, (
        "Got None for xpath expression from %s" % repr(css_expr))
    if prefix:
        expr.add_prefix(prefix)
    return _unicode(expr)
