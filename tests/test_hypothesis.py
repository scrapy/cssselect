from __future__ import annotations

import re
import typing
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from lxml import etree

from cssselect import GenericTranslator, HTMLTranslator, SelectorError, parse
from cssselect.parser import (
    Token,
    TokenStream,
    _class_re,
    _el_re,
    _id_re,
    _serialize_ident,
    parse_selector_group,
    parse_series,
    tokenize,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from cssselect.parser import Selector


WHITESPACE = " \t\n\r\f"
# Characters not allowed in XML 1.0, which lxml also rejects in XPath
# expressions, except NUL and surrogates, which the tokenizer replaces with
# U+FFFD.
NON_XML_CHARS = "".join(
    map(chr, [*range(0x1, 0x9), 0xB, 0xC, *range(0xE, 0x20), 0xFFFE, 0xFFFF])
)

ATTRIB_OPERATORS: dict[str, Callable[[str, str], bool]] = {
    "=": lambda value, arg: value == arg,
    "!=": lambda value, arg: value != arg,
    "^=": lambda value, arg: arg != "" and value.startswith(arg),
    "$=": lambda value, arg: arg != "" and value.endswith(arg),
    "*=": lambda value, arg: arg != "" and arg in value,
    "~=": lambda value, arg: (
        arg != ""
        and not any(c in WHITESPACE for c in arg)
        and arg in re.split(f"[{WHITESPACE}]+", value)
    ),
    "|=": lambda value, arg: value == arg or value.startswith(arg + "-"),
}

CSS_FRAGMENTS = [
    *"abc*>+~,.#[]=^$|!()'\":- \\019nN",
    ":not(",
    ":has(",
    ":is(",
    ":where(",
    ":nth-child(",
    ":lang(",
    ":contains(",
    ":scope",
    "::",
    "\\41 ",
]

ESCAPE_CONTEXTS = [
    "{}",
    ".{}",
    "#{}",
    "a[x={}]",
    "a[x='{}']",
    ":contains('{}')",
]

attrib_text: st.SearchStrategy[str] = st.text(
    st.sampled_from([*"aAb- '\"\t\n"]), max_size=6
)
xml_text: st.SearchStrategy[str] = st.text(
    st.characters(exclude_categories=["Cs"], exclude_characters="\0" + NON_XML_CHARS)
)


def preprocess(s: str) -> str:
    """Replace NUL and surrogates with U+FFFD, like the tokenizer does."""
    return re.sub("[\0\ud800-\udfff]", "\N{REPLACEMENT CHARACTER}", s)


def check_canonical(selectors: list[Selector]) -> None:
    for selector in selectors:
        canonical = selector.canonical()
        reparsed = parse(canonical)
        assert len(reparsed) == 1
        assert reparsed[0].canonical() == canonical
        assert reparsed[0].specificity() == selector.specificity()


@given(st.text(min_size=1))
def test_serialize_ident_roundtrip(s: str) -> None:
    tokens = list(tokenize(_serialize_ident(s)))
    assert [token.type for token in tokens] == ["IDENT", "EOF"]
    assert tokens[0].value == preprocess(s)


@given(st.text())
def test_string_css_roundtrip(s: str) -> None:
    tokens = list(tokenize(Token("STRING", s, 0).css()))
    assert [token.type for token in tokens] == ["STRING", "EOF"]
    assert tokens[0].value == preprocess(s)


@given(xml_text)
def test_xpath_literal_roundtrip(s: str) -> None:
    literal = GenericTranslator.xpath_literal(s)
    assert etree.XPath(literal)(etree.Element("x")) == s


@given(st.integers(), st.integers())
def test_parse_series(a: int, b: int) -> None:
    tokens = [token for token in tokenize(f"{a}n{b:+d}") if token.type != "EOF"]
    assert parse_series(tokens) == (a, b)


@given(
    st.sampled_from(["nth-child", "nth-last-child", "nth-of-type", "nth-last-of-type"]),
    st.integers(-6, 6),
    st.integers(-6, 12),
    st.lists(st.sampled_from(["c", "d"]), max_size=12),
)
def test_nth_child(function: str, a: int, b: int, names: list[str]) -> None:
    root = etree.Element("r")
    for name in names:
        etree.SubElement(root, name)
    xpath = GenericTranslator().css_to_xpath(f"c:{function}({a}n{b:+d})")
    selected = [
        root.index(element)
        for element in typing.cast("list[etree._Element]", root.xpath(xpath))
    ]

    siblings = list(range(len(names)))
    if function.endswith("-of-type"):
        siblings = [i for i in siblings if names[i] == "c"]
    if "-last-" in function:
        siblings.reverse()
    expected = [
        i
        for i in range(len(names))
        if names[i] == "c"
        and any(
            a * k + b == siblings.index(i) + 1 for k in range(len(names) + abs(b) + 1)
        )
    ]
    assert selected == expected


@given(
    st.sampled_from(sorted(ATTRIB_OPERATORS)),
    st.sampled_from(["", " i", " s"]),
    attrib_text,
    attrib_text,
)
def test_attrib_operators(operator: str, flag: str, value: str, arg: str) -> None:
    element = etree.Element("e", a=value)
    css = f"e[a{operator}{Token('STRING', arg, 0).css()}{flag}]"
    xpath = GenericTranslator().css_to_xpath(css)
    if flag == " i":
        # The alphabet is ASCII-only, so str.lower() is ASCII lowercasing.
        value, arg = value.lower(), arg.lower()
    assert bool(etree.XPath(xpath)(element)) == ATTRIB_OPERATORS[operator](value, arg)


@given(st.from_regex(_el_re) | st.from_regex(_id_re) | st.from_regex(_class_re))
def test_parse_fast_path(css: str) -> None:
    stream = TokenStream(tokenize(css), css)
    assert repr(parse(css)) == repr(list(parse_selector_group(stream)))


@given(st.text())
def test_parse_canonical(css: str) -> None:
    try:
        selectors = parse(css)
    except SelectorError:
        return
    check_canonical(selectors)


@given(st.lists(st.sampled_from(CSS_FRAGMENTS), max_size=20).map("".join))
def test_css_like(css: str) -> None:
    for translator in (GenericTranslator(), HTMLTranslator()):
        try:
            xpath = translator.css_to_xpath(css)
        except SelectorError:
            continue
        # Escapes like "\b" can produce characters not allowed in XML, a known
        # problem tested by test_escape_translates_non_xml().
        if not any(c in NON_XML_CHARS for c in xpath):
            etree.XPath(xpath)
    try:
        selectors = parse(css)
    except SelectorError:
        return
    check_canonical(selectors)


def check_escape_translates(context: str, char: str) -> None:
    css = context.format(f"\\{ord(char):x} ")
    for translator in (GenericTranslator(), HTMLTranslator()):
        etree.XPath(translator.css_to_xpath(css))


@given(
    st.sampled_from(ESCAPE_CONTEXTS),
    st.characters(exclude_characters=NON_XML_CHARS),
)
def test_escape_translates(context: str, char: str) -> None:
    check_escape_translates(context, char)


@pytest.mark.xfail(
    raises=ValueError,
    strict=True,
    reason="Characters not allowed in XML end up in the XPath expression",
)
@given(st.sampled_from(ESCAPE_CONTEXTS), st.sampled_from(NON_XML_CHARS))
def test_escape_translates_non_xml(context: str, char: str) -> None:
    check_escape_translates(context, char)
