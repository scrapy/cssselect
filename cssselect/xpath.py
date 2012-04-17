"""
    cssselect.xpath
    ===============

    Translation of parsed CSS selectors to XPath expressions.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import re
from cssselect.parser import parse, parse_series, Element, SelectorError


try:
    _basestring = basestring
    _unicode = unicode
except NameError:
    # Python 3
    _basestring = str
    _unicode = str


class ExpressionError(SelectorError, RuntimeError):
    """Inexistent or unsupported selector (eg. pseudo-class)."""


#### XPath Helpers

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
        self.add_condition(
            "name() = %s" % GenericTranslator.xpath_literal(self.element))
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
        return self


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


#### Translation

class GenericTranslator(object):
    """
    Translator for "generic" XML documents.
    """
    combinator_mapping = {
        ' ': 'descendant',
        '>': 'child',
        '+': 'direct_adjacent',
        '~': 'indirect_adjacent',
    }

    attribute_operator_mapping = {
       'exists': 'exists',
        '=': 'equals',
        '~=': 'includes',
        '|=': 'dashmatch',
        '^=': 'prefixmatch',
        '$=': 'suffixmatch',
        '*=': 'substringmatch',
        '!=': 'different',  # XXX Not in Level 3 but meh
    }

    def css_to_xpath(self, css, prefix='descendant-or-self::'):
        """Translate a CSS Selector to XPath.

        :param css: An Unicode string or a parsed selector object.
        :returns: An Unicode string.

        .. sourcecode:: pycon

            >>> from cssselect import GenericTranslator
            >>> expression = GenericTranslator().css_to_xpath('div.content')
            >>> print(expression)
            descendant-or-self::div[@class and contains(concat(' ', normalize-space(@class), ' '), ' content ')]

        The resulting expression can be used with lxml's `XPath engine`_:

        .. _XPath engine: http://lxml.de/xpathxslt.html#xpath

        .. sourcecode:: pycon

            >>> from lxml.etree import fromstring
            >>> document = fromstring('''<div id="outer">
            ...   <div id="inner" class="content body">
            ...       text
            ...   </div></div>''')
            >>> [e.get('id') for e in document.xpath(expression)]
            ['inner']

        """
        if isinstance(css, _basestring):
            selector = parse(css)
        else:
            selector = css  # assume it is already parsed
        xpath = self.xpath(selector)
        xpath.add_prefix(prefix or '')
        return _unicode(xpath)

    @staticmethod
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

    def xpath(self, parsed_selector, prefix=None):
        """Translate any parsed selector object."""
        type_name = type(parsed_selector).__name__
        method = getattr(self, 'xpath_%s' % type_name.lower(), None)
        if not method:
            raise TypeError('Expected a parsed selector, got %s' % type_name)
        return method(parsed_selector)


    # Dispatched by parsed object type

    def xpath_or(self, selector_group):
        """Translate a group of selectors (class Or)."""
        return XPathExprOr([self.xpath(item) for item in selector_group.items])

    def xpath_combinedselector(self, combined):
        """Translate a combined selector."""
        combinator = self.combinator_mapping.get(combined.combinator)
        if not combinator:
            raise ExpressionError(
                "Unknown combinator: %r" % combined.combinator)
        method = getattr(self, 'xpath_%s_combinator' % combinator)
        return method(self.xpath(combined.selector),
                      self.xpath(combined.subselector))

    def xpath_function(self, function):
        """Translate a functional pseudo-class."""
        method = 'xpath_%s_function' % function.name.replace('-', '_')
        method = getattr(self, method, None)
        if not method:
            raise ExpressionError(
                "The pseudo-class :%s() is unknown" % function.name)
        return method(self.xpath(function.selector), function)

    def xpath_pseudo(self, pseudo):
        """Translate a pseudo-class."""
        method = 'xpath_%s_pseudo' % pseudo.ident.replace('-', '_')
        method = getattr(self, method, None)
        if not method:
            # TODO: better error message for pseudo-elements?
            raise ExpressionError(
                "The pseudo-class :%s is unknown" % pseudo.ident)
        return method(self.xpath(pseudo.selector))


    def xpath_attrib(self, selector):
        """Translate an attribute selector."""
        operator = self.attribute_operator_mapping.get(selector.operator)
        if not operator:
            raise ExpressionError(
                "Unknown attribute operator: %r" % selector.operator)
        method = getattr(self, 'xpath_attrib_%s' % operator)
        # FIXME: what if attrib is *?
        if selector.namespace == '*':
            name = '@' + selector.attrib
        else:
            name = '@%s:%s' % (selector.namespace, selector.attrib)
        return method(self.xpath(selector.selector), name, selector.value)

    def xpath_class(self, class_selector):
        """Translate a class selector."""
        # .foo is defined as [class~=foo] in the spec.
        xpath = self.xpath(class_selector.selector)
        return self.xpath_attrib_includes(
            xpath, '@class', class_selector.class_name)

    def xpath_hash(self, id_selector):
        """Translate an ID selector."""
        xpath = self.xpath(id_selector.selector)
        xpath.add_condition('@id = %s' % self.xpath_literal(id_selector.id))
        return xpath

    def xpath_element(self, selector):
        """Translate a type or universal selector."""
        if selector.namespace == '*':
            element = selector.element.lower()
        else:
            # FIXME: Should we lowercase here?
            element = '%s:%s' % (selector.namespace, selector.element)
        return XPathExpr(element=element)


    # CombinedSelector: dispatch by combinator

    def xpath_descendant_combinator(self, left, right):
        """right is a child, grand-child or further descendant of left"""
        return left.join('/descendant-or-self::*/', right)

    def xpath_child_combinator(self, left, right):
        """right is an immediate child of left"""
        return left.join('/', right)

    def xpath_direct_adjacent_combinator(self, left, right):
        """right is a sibling immediately after left"""
        xpath = left.join('/following-sibling::', right)
        xpath.add_name_test()
        xpath.add_condition('position() = 1')
        return xpath

    def xpath_indirect_adjacent_combinator(self, left, right):
        """right is a sibling after left, immediately or not"""
        return left.join('/following-sibling::', right)


    # Function: dispatch by function/pseudo-class name

    def xpath_nth_child_function(self, xpath, function, last=False,
                                 add_name_test=True):
        a, b = parse_series(function.arguments)
        if not a and not b and not last:
            # a=0 means nothing is returned...
            xpath.add_condition('false() and position() = 0')
            return xpath
        if add_name_test:
            xpath.add_name_test()
        xpath.add_star_prefix()
        if a == 0:
            if last:
                b = 'last() - %s' % b
            xpath.add_condition('position() = %s' % b)
            return xpath
        if last:
            # FIXME: I'm not sure if this is right
            a = -a
            b = -b
        if b > 0:
            b_neg = str(-b)
        else:
            b_neg = '+%s' % (-b)
        if a != 1:
            expr = ['(position() %s) mod %s = 0' % (b_neg, a)]
        else:
            expr = []
        if b >= 0:
            expr.append('position() >= %s' % b)
        elif b < 0 and last:
            expr.append('position() < (last() %s)' % b)
        expr = ' and '.join(expr)
        if expr:
            xpath.add_condition(expr)
        return xpath
        # FIXME: handle an+b, odd, even
        # an+b means every-a, plus b, e.g., 2n+1 means odd
        # 0n+b means b
        # n+0 means a=1, i.e., all elements
        # an means every a elements, i.e., 2n means even
        # -n means -1n
        # -1n+6 means elements 6 and previous

    def xpath_nth_last_child_function(self, xpath, function):
        return self.xpath_nth_child_function(xpath, function, last=True)

    def xpath_nth_of_type_function(self, xpath, function):
        if xpath.element == '*':
            raise ExpressionError(
                "*:nth-of-type() is not implemented")
        return self.xpath_nth_child_function(xpath, function,
                                             add_name_test=False)

    def xpath_nth_last_of_type_function(self, xpath, function):
        if xpath.element == '*':
            raise ExpressionError(
                "*:nth-of-type() is not implemented")
        return self.xpath_nth_child_function(xpath, function, last=True,
                                             add_name_test=False)

    def xpath_not_function(self, xpath, function):
        condition = self.xpath(function.arguments).condition
        # FIXME: should I do something about element_path?
        xpath.add_condition('not(%s)' % condition)
        return xpath

    def xpath_contains_function(self, xpath, function):
        xpath.add_condition('contains(string(.), %s)'
                            % self.xpath_literal(function.arguments))
        return xpath

    def function_unsupported(self, xpath, pseudo):
        raise ExpressionError(
            "The pseudo-class :%s() is not supported" % pseudo.name)

    xpath_lang_function = function_unsupported


    # Pseudo: dispatch by pseudo-class name

    def xpath_root_pseudo(self, xpath):
        xpath.add_condition("not(parent::*)")
        return xpath

    def xpath_first_child_pseudo(self, xpath):
        xpath.add_star_prefix()
        xpath.add_name_test()
        xpath.add_condition('position() = 1')
        return xpath

    def xpath_last_child_pseudo(self, xpath):
        xpath.add_star_prefix()
        xpath.add_name_test()
        xpath.add_condition('position() = last()')
        return xpath

    def xpath_first_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:first-of-type is not implemented")
        xpath.add_star_prefix()
        xpath.add_condition('position() = 1')
        return xpath

    def xpath_last_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:last-of-type is not implemented")
        xpath.add_star_prefix()
        xpath.add_condition('position() = last()')
        return xpath

    def xpath_only_child_pseudo(self, xpath):
        xpath.add_name_test()
        xpath.add_star_prefix()
        xpath.add_condition('last() = 1')
        return xpath

    def xpath_only_of_type_pseudo(self, xpath):
        if xpath.element == '*':
            raise ExpressionError(
                "*:only-of-type is not implemented")
        xpath.add_condition('last() = 1')
        return xpath

    def xpath_empty_pseudo(self, xpath):
        xpath.add_condition("not(*) and not(normalize-space())")
        return xpath

    def pseudo_never_matches(self, xpath):
        """Common implementation for pseudo-classes that never match."""
        xpath.add_condition("0")
        return xpath

    xpath_link_pseudo = pseudo_never_matches
    xpath_visited_pseudo = pseudo_never_matches
    xpath_hover_pseudo = pseudo_never_matches
    xpath_active_pseudo = pseudo_never_matches
    xpath_focus_pseudo = pseudo_never_matches
    xpath_target_pseudo = pseudo_never_matches
    xpath_enabled_pseudo = pseudo_never_matches
    xpath_disabled_pseudo = pseudo_never_matches
    xpath_checked_pseudo = pseudo_never_matches

    # Attrib: dispatch by attribute operator

    def xpath_attrib_exists(self, xpath, name, value):
        assert not value
        xpath.add_condition(name)
        return xpath

    def xpath_attrib_equals(self, xpath, name, value):
        xpath.add_condition('%s = %s' % (name, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_different(self, xpath, name, value):
        # FIXME: this seems like a weird hack...
        if value:
            xpath.add_condition('not(%s) or %s != %s'
                                % (name, name, self.xpath_literal(value)))
        else:
            xpath.add_condition('%s != %s'
                                % (name, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_includes(self, xpath, name, value):
        xpath.add_condition(
            "%s and contains(concat(' ', normalize-space(%s), ' '), %s)"
            % (name, name, self.xpath_literal(' '+value+' ')))
        return xpath

    def xpath_attrib_dashmatch(self, xpath, name, value):
        # Weird, but true...
        xpath.add_condition('%s and (%s = %s or starts-with(%s, %s))' % (
            name,
            name, self.xpath_literal(value),
            name, self.xpath_literal(value + '-')))
        return xpath

    def xpath_attrib_prefixmatch(self, xpath, name, value):
        xpath.add_condition('%s and starts-with(%s, %s)' % (
            name, name, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_suffixmatch(self, xpath, name, value):
        # Oddly there is a starts-with in XPath 1.0, but not ends-with
        xpath.add_condition(
            '%s and substring(%s, string-length(%s)-%s) = %s'
            % (name, name, name, len(value)-1, self.xpath_literal(value)))
        return xpath

    def xpath_attrib_substringmatch(self, xpath, name, value):
        # Attribute selectors are case sensitive
        xpath.add_condition('%s and contains(%s, %s)' % (
            name, name, self.xpath_literal(value)))
        return xpath


class HTMLTranslator(GenericTranslator):
    """
    Translator for HTML documents.
    """
    def xpath_checked_pseudo(self, xpath):
        # FIXME: is this really all the elements?
        xpath.add_condition(
            "(@selected and name(.) = 'option') or "
            "(@checked and name(.) = 'input')")
        return xpath

    def xpath_link_pseudo(self, xpath):
        xpath.add_condition("@href and name(.) = 'a'")
        return xpath

    # Links are never visited, the implementation for :visited is the same
    # as in GenericTranslator

    def xpath_disabled_pseudo(self, xpath):
        # http://www.w3.org/TR/html5/section-index.html#attributes-1
        xpath.add_condition('''
        (
            @disabled and
            (
                name(.) = 'input' or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea' or
                name(.) = 'keygen' or
                name(.) = 'command' or
                name(.) = 'fieldset' or
                name(.) = 'optgroup' or
                name(.) = 'option'
            )
        ) or (
            (
                name(.) = 'input' or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea' or
                name(.) = 'keygen'
            )
            and ancestor::fieldset[@disabled]
        )
        ''')
        # FIXME: in the second half, add "and is not a descendant of that
        # fieldset element's first legend element child, if any."
        return xpath

    def xpath_enabled_pseudo(self, xpath):
        # http://www.w3.org/TR/html5/section-index.html#attributes-1
        xpath.add_condition('''
        (
            (
                name(.) = 'command' or
                name(.) = 'fieldset' or
                name(.) = 'optgroup' or
                name(.) = 'option'
            )
            and not(@disabled)
        ) or (
            (
                name(.) = 'input' or
                name(.) = 'button' or
                name(.) = 'select' or
                name(.) = 'textarea' or
                name(.) = 'keygen'
            )
            and not (@disabled or ancestor::fieldset[@disabled])
        )
        ''')
        # FIXME: in the second half, add "and is not a descendant of that
        # fieldset element's first legend element child, if any."
        return xpath
