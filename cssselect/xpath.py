"""
    cssselect.xpath
    ===============

    Translation of parsed CSS selectors to XPath expressions.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import re

from cssselect.parser import Element, _unicode


class XPathExpr(object):

    def __init__(self, prefix=None, path=None, element='*', condition=None,
                 star_prefix=False):
        self.prefix = prefix
        self.path = path
        self.element = element
        self.condition = condition
        self.star_prefix = star_prefix

    def __str__(self):
        path = ''
        if self.prefix is not None:
            path += _unicode(self.prefix)
        if self.path is not None:
            path += _unicode(self.path)
        path += _unicode(self.element)
        if self.condition:
            path += '[%s]' % self.condition
        return path

    def __repr__(self):
        return '%s[%s]' % (
            self.__class__.__name__, self)

    def add_condition(self, condition):
        if self.condition:
            self.condition = '%s and (%s)' % (self.condition, condition)
        else:
            self.condition = condition

    def add_path(self, part):
        if self.path is None:
            self.path = self.element
        else:
            self.path += self.element
        self.element = part

    def add_prefix(self, prefix):
        if self.prefix:
            self.prefix = prefix + self.prefix
        else:
            self.prefix = prefix

    def add_name_test(self):
        if self.element == '*':
            # We weren't doing a test anyway
            return
        self.add_condition("name() = %s" % xpath_literal(self.element))
        self.element = '*'

    def add_star_prefix(self):
        """
        Adds a /* prefix if there is no prefix.  This is when you need
        to keep context's constrained to a single parent.
        """
        if self.path:
            self.path += '*/'
        else:
            self.path = '*/'
        self.star_prefix = True

    def join(self, combiner, other):
        prefix = _unicode(self)
        prefix += combiner
        path = (other.prefix or '') + (other.path or '')
        # We don't need a star prefix if we are joining to this other
        # prefix; so we'll get rid of it
        if other.star_prefix and path == '*/':
            path = ''
        self.prefix = prefix
        self.path = path
        self.element = other.element
        self.condition = other.condition

class XPathExprOr(XPathExpr):
    """
    Represents |'d expressions.  Note that unfortunately it isn't
    the union, it's the sum, so duplicate elements will appear.
    """

    def __init__(self, items, prefix=None):
        for item in items:
            assert item is not None
        self.items = items
        self.prefix = prefix

    def __str__(self):
        prefix = self.prefix or ''
        return ' | '.join(["%s%s" % (prefix,i) for i in self.items])

split_at_single_quotes = re.compile("('+)").split

def xpath_literal(s):
    if isinstance(s, Element):
        # This is probably a symbol that looks like an expression...
        s = s._format_element()
    else:
        s = _unicode(s)
    if "'" not in s:
        s = "'%s'" % s
    elif '"' not in s:
        s = '"%s"' % s
    else:
        s = "concat(%s)" % ','.join([
            (("'" in part) and '"%s"' or "'%s'") % part
            for part in split_at_single_quotes(s) if part
            ])
    return s
