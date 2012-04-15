"""
    cssselect.parser
    ================

    Tokenizer, parser and parsed objects for CSS selectors.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

import re


try:
    _unicode = unicode
    _unichr = unichr
except NameError:
    # Python 3
    _unicode = str
    _unichr = chr


class SelectorError(Exception):
    """Invalid or unsupported selector.

    Common parent class for the exceptions that are actually raised.
    You can use it to catch any error in a selector.

    """

class SelectorSyntaxError(SelectorError, SyntaxError):
    """Parsing a selector that does not match the grammar."""


#### Parsed objects

class Class(object):
    """
    Represents selector.class_name
    """

    def __init__(self, selector, class_name):
        self.selector = selector
        self.class_name = class_name

    def __repr__(self):
        return '%s[%r.%s]' % (
            self.__class__.__name__,
            self.selector,
            self.class_name)


class Function(object):
    """
    Represents selector:name(expr)
    """

    def __init__(self, selector, type, name, arguments):
        self.selector = selector
        self.type = type  # TODO: is this needed?
        self.name = name
        self.arguments = arguments

    def __repr__(self):
        return '%s[%r%s%s(%r)]' % (
            self.__class__.__name__,
            self.selector,
            self.type, self.name, self.arguments)


class Pseudo(object):
    """
    Represents selector:ident
    """

    def __init__(self, selector, type, ident):
        self.selector = selector
        assert type in (':', '::')
        self.type = type
        self.ident = ident

    def __repr__(self):
        return '%s[%r%s%s]' % (
            self.__class__.__name__,
            self.selector,
            self.type, self.ident)


class Attrib(object):
    """
    Represents selector[namespace|attrib operator value]
    """

    def __init__(self, selector, namespace, attrib, operator, value):
        self.selector = selector
        self.namespace = namespace
        self.attrib = attrib
        self.operator = operator
        self.value = value

    def __repr__(self):
        if self.operator == 'exists':
            return '%s[%r[%s]]' % (
                self.__class__.__name__,
                self.selector,
                self._format_attrib())
        else:
            return '%s[%r[%s %s %r]]' % (
                self.__class__.__name__,
                self.selector,
                self._format_attrib(),
                self.operator,
                self.value)

    def _format_attrib(self):
        if self.namespace == '*':
            return self.attrib
        else:
            return '%s|%s' % (self.namespace, self.attrib)


class Element(object):
    """
    Represents namespace|element
    """

    def __init__(self, namespace, element):
        self.namespace = namespace
        self.element = element

    def __repr__(self):
        return '%s[%s]' % (
            self.__class__.__name__,
            self._format_element())

    def _format_element(self):
        if self.namespace == '*':
            return self.element
        else:
            return '%s|%s' % (self.namespace, self.element)


class Hash(object):
    """
    Represents selector#id
    """

    def __init__(self, selector, id):
        self.selector = selector
        self.id = id

    def __repr__(self):
        return '%s[%r#%s]' % (
            self.__class__.__name__,
            self.selector, self.id)


class Or(object):

    def __init__(self, items):
        self.items = items
    def __repr__(self):
        return '%s(%r)' % (
            self.__class__.__name__,
            self.items)


class CombinedSelector(object):

    def __init__(self, selector, combinator, subselector):
        assert selector is not None
        self.selector = selector
        self.combinator = combinator
        self.subselector = subselector

    def __repr__(self):
        if self.combinator == ' ':
            comb = '<followed>'
        else:
            comb = self.combinator
        return '%s[%r %s %r]' % (
            self.__class__.__name__,
            self.selector,
            comb,
            self.subselector)


#### Parser

_el_re = re.compile(r'^\w+\s*$', re.UNICODE)
_id_re = re.compile(r'^(\w*)#(\w+)\s*$', re.UNICODE)
_class_re = re.compile(r'^(\w*)\.(\w+)\s*$', re.UNICODE)


def parse(string):
    # Fast path for simple cases
    match = _el_re.match(string)
    if match:
        return Element('*', match.group(0).strip())
    match = _id_re.match(string)
    if match is not None:
        return Hash(Element('*', match.group(1) or '*'), match.group(2))
    match = _class_re.match(string)
    if match is not None:
        return Class(Element('*', match.group(1) or '*'), match.group(2))

    stream = TokenStream(tokenize(string))
    stream.source = string
    try:
        return parse_selector_group(stream)
    except SelectorSyntaxError:
        import sys
        e = sys.exc_info()[1]
        message = "%s at %s -> %r" % (
            e, stream.used, stream.peek())
        e.msg = message
        if sys.version_info < (2,6):
            e.message = message
        e.args = tuple([message])
        raise


def parse_selector_group(stream):
    result = []
    while 1:
        result.append(parse_selector(stream))
        if stream.peek() == ',':
            stream.next()
            # Ignore optional whitespace after a group separator
            if stream.peek() == ' ':
                stream.next()
        else:
            break
    if len(result) == 1:
        return result[0]
    else:
        return Or(result)


def parse_selector(stream):
    consumed = len(stream.used)
    result = parse_simple_selector(stream)
    if consumed == len(stream.used):
        raise SelectorSyntaxError(
            "Expected selector, got '%s'" % stream.peek())
    while 1:
        peek = stream.peek()
        if peek == ',' or peek is None:
            return result
        elif peek in ('+', '>', '~'):
            # A combinator
            combinator = stream.next()
            # Ignore optional whitespace after a combinator
            if stream.peek() == ' ':
                stream.next()
        else:
            combinator = ' '
        consumed = len(stream.used)
        next_selector = parse_simple_selector(stream)
        if consumed == len(stream.used):
            raise SelectorSyntaxError(
                "Expected selector, got '%s'" % stream.peek())
        result = CombinedSelector(result, combinator, next_selector)
    return result


def parse_simple_selector(stream):
    peek = stream.peek()
    if peek != '*' and not isinstance(peek, Symbol):
        element = namespace = '*'
    else:
        next = stream.next()
        if next != '*' and not isinstance(next, Symbol):
            raise SelectorSyntaxError(
                "Expected symbol, got '%s'" % next)
        if stream.peek() == '|':
            namespace = next
            stream.next()
            element = stream.next()
            if element != '*' and not isinstance(next, Symbol):
                raise SelectorSyntaxError(
                    "Expected symbol, got '%s'" % next)
        else:
            namespace = '*'
            element = next
    result = Element(namespace, element)
    has_hash = False
    while 1:
        peek = stream.peek()
        if peek == '#':
            if has_hash:
                # You can't have two hashes
                # (FIXME: is there some more general rule I'm missing?)
                break
            stream.next()
            result = Hash(result, stream.next())
            has_hash = True
            continue
        elif peek == '.':
            stream.next()
            result = Class(result, stream.next())
            continue
        elif peek == '[':
            stream.next()
            result = parse_attrib(result, stream)
            next = stream.next()
            if not next == ']':
                raise SelectorSyntaxError(
                    "] expected, got '%s'" % next)
            continue
        elif peek == ':' or peek == '::':
            type = stream.next()
            ident = stream.next()
            if not isinstance(ident, Symbol):
                raise SelectorSyntaxError(
                    "Expected symbol, got '%s'" % ident)
            if stream.peek() == '(':
                stream.next()
                peek = stream.peek()
                if isinstance(peek, String):
                    selector = stream.next()
                elif isinstance(peek, Symbol) and is_int(peek):
                    selector = int(stream.next())
                else:
                    # FIXME: parse_simple_selector, or selector, or...?
                    selector = parse_simple_selector(stream)
                next = stream.next()
                if not next == ')':
                    raise SelectorSyntaxError(
                        "Expected ')', got '%s' and '%s'"
                        % (next, selector))
                result = Function(result, type, ident, selector)
            else:
                result = Pseudo(result, type, ident)
            continue
        else:
            if peek == ' ':
                stream.next()
            break
        # FIXME: not sure what "negation" is
    return result


def is_int(v):
    try:
        int(v)
    except ValueError:
        return False
    else:
        return True


def parse_attrib(selector, stream):
    attrib = stream.next()
    if stream.peek() == '|':
        namespace = attrib
        stream.next()
        attrib = stream.next()
    else:
        namespace = '*'
    if stream.peek() == ']':
        return Attrib(selector, namespace, attrib, 'exists', None)
    op = stream.next()
    if not op in ('^=', '$=', '*=', '=', '~=', '|=', '!='):
        raise SelectorSyntaxError(
            "Operator expected, got '%s'" % op)
    value = stream.next()
    if not isinstance(value, (Symbol, String)):
        raise SelectorSyntaxError(
            "Expected string or symbol, got '%s'" % value)
    return Attrib(selector, namespace, attrib, op, value)


def parse_series(s):
    """
    Parses things like '1n+2', or 'an+b' generally, returning (a, b)
    """
    if isinstance(s, Element):
        s = s._format_element()
    if not s or s == '*':
        # Happens when there's nothing, which the CSS parser thinks of as *
        return (0, 0)
    if isinstance(s, int):
        # Happens when you just get a number
        return (0, s)
    if s == 'odd':
        return (2, 1)
    elif s == 'even':
        return (2, 0)
    elif s == 'n':
        return (1, 0)
    if 'n' not in s:
        # Just a b
        return (0, int(s))
    a, b = s.split('n', 1)
    if not a:
        a = 1
    elif a == '-' or a == '+':
        a = int(a+'1')
    else:
        a = int(a)
    if not b:
        b = 0
    elif b == '-' or b == '+':
        b = int(b+'1')
    else:
        b = int(b)
    return (a, b)


#### Token objects

class _UniToken(_unicode):
    def __new__(cls, contents, pos):
        obj = _unicode.__new__(cls, contents)
        obj.pos = pos
        return obj

    def __repr__(self):
        return '%s(%s, %r)' % (
            self.__class__.__name__,
            _unicode.__repr__(self),
            self.pos)

class Symbol(_UniToken):
    pass

class String(_UniToken):
    pass

class Token(_UniToken):
    pass


#### Tokenizer

_match_whitespace = re.compile(r'\s+', re.UNICODE).match

_replace_comments = re.compile(r'/\*.*?\*/', re.DOTALL).sub

_match_count_number = re.compile(r'[+-]?\d*n(?:[+-]\d+)?').match

def tokenize(s):
    pos = 0
    s = _replace_comments('', s)
    while 1:
        match = _match_whitespace(s, pos=pos)
        if match:
            preceding_whitespace_pos = pos
            pos = match.end()
        else:
            preceding_whitespace_pos = 0
        if pos >= len(s):
            return
        match = _match_count_number(s, pos=pos)
        if match and match.group() != 'n':
            sym = s[pos:match.end()]
            yield Symbol(sym, pos)
            pos = match.end()
            continue
        c = s[pos]
        c2 = s[pos:pos+2]
        if c2 in ('~=', '|=', '^=', '$=', '*=', '::', '!='):
            if c2 == '::' and preceding_whitespace_pos > 0:
                yield Token(' ', preceding_whitespace_pos)
            yield Token(c2, pos)
            pos += 2
            continue
        if c in '>+~,.*=[]()|:#':
            if c in ':.#[' and preceding_whitespace_pos > 0:
                yield Token(' ', preceding_whitespace_pos)
            yield Token(c, pos)
            pos += 1
            continue
        if c == '"' or c == "'":
            # Quoted string
            old_pos = pos
            sym, pos = tokenize_escaped_string(s, pos)
            yield String(sym, old_pos)
            continue
        old_pos = pos
        sym, pos = tokenize_symbol(s, pos)
        yield Symbol(sym, old_pos)
        continue

split_at_string_escapes = re.compile(r'(\\(?:%s))'
                                     % '|'.join(['[A-Fa-f0-9]{1,6}(?:\r\n|\s)?',
                                                 '[^A-Fa-f0-9]'])).split


def unescape_string_literal(literal):
    substrings = []
    for substring in split_at_string_escapes(literal):
        if not substring:
            continue
        elif '\\' in substring:
            if substring[0] == '\\' and len(substring) > 1:
                substring = substring[1:]
                if substring[0] in '0123456789ABCDEFabcdef':
                    # int() correctly ignores the potentially trailing whitespace
                    substring = _unichr(int(substring, 16))
            else:
                raise SelectorSyntaxError(
                    "Invalid escape sequence %r in string %r"
                    % (substring.split('\\')[1], literal))
        substrings.append(substring)
    return ''.join(substrings)


def tokenize_escaped_string(s, pos):
    quote = s[pos]
    assert quote in ('"', "'")
    pos = pos+1
    start = pos
    while 1:
        next = s.find(quote, pos)
        if next == -1:
            raise SelectorSyntaxError(
                "Expected closing %s for string in: %r"
                % (quote, s[start:]))
        result = s[start:next]
        if result.endswith('\\'):
            # next quote character is escaped
            pos = next+1
            continue
        if '\\' in result:
            result = unescape_string_literal(result)
        return result, next+1


_illegal_symbol = re.compile(r'[^\w\\-]', re.UNICODE)

def tokenize_symbol(s, pos):
    start = pos
    match = _illegal_symbol.search(s, pos=pos)
    if not match:
        # Goes to end of s
        return s[start:], len(s)
    if match.start() == pos:
        raise SelectorSyntaxError(
            "Unexpected symbol: %r" % s[pos])
    if not match:
        result = s[start:]
        pos = len(s)
    else:
        result = s[start:match.start()]
        pos = match.start()
    try:
        result = result.encode('ASCII', 'backslashreplace').decode('unicode_escape')
    except UnicodeDecodeError:
        import sys
        e = sys.exc_info()[1]
        raise SelectorSyntaxError(
            "Bad symbol %r: %s" % (result, e))
    return result, pos


class TokenStream(object):

    def __init__(self, tokens, source=None):
        self.used = []
        self.tokens = iter(tokens)
        self.source = source
        self.peeked = None
        self._peeking = False
        try:
            self.next_token = self.tokens.next
        except AttributeError:
            # Python 3
            self.next_token = self.tokens.__next__

    def next(self):
        if self._peeking:
            self._peeking = False
            self.used.append(self.peeked)
            return self.peeked
        else:
            try:
                next = self.next_token()
                self.used.append(next)
                return next
            except StopIteration:
                return None

    def __iter__(self):
        return iter(self.next, None)

    def peek(self):
        if not self._peeking:
            try:
                self.peeked = self.next_token()
            except StopIteration:
                return None
            self._peeking = True
        return self.peeked
