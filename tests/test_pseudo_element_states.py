"""Parsing states of pseudo-elements without applying them to their origin."""

from __future__ import annotations

import pytest
from lxml import html

import cssselect
from cssselect import ExpressionError, GenericTranslator, SelectorSyntaxError, parse
from cssselect.parser import FunctionalPseudoElement


@pytest.mark.parametrize(
    ("source", "canonical", "specificity"),
    [
        (".something::before:hover", ".something::before:hover", (0, 2, 1)),
        ("a:before:active", "a::before:active", (0, 1, 2)),
        ("A::BEFORE:HOVER:FOCUS", "A::before:hover:focus", (0, 2, 2)),
        ("::first-line:focus-visible", "::first-line:focus-visible", (0, 1, 1)),
        ("::after:focus-within", "::after:focus-within", (0, 1, 1)),
        ("a::part(tab):hover", "a::part(tab):hover", (0, 1, 2)),
        ("#id::before:not(:hover)", "#id::before:not(:hover)", (1, 1, 1)),
        (
            "p::before:is(:hover,:focus:active)",
            "p::before:is(:hover, :focus:active)",
            (0, 2, 2),
        ),
        ("p::after:hover:where(:focus)", "p::after:hover:where(:focus)", (0, 1, 2)),
        ("p::after:where(:hover):active", "p::after:where(:hover):active", (0, 1, 2)),
        (
            "p::before:not(:is(:hover,:active))",
            "p::before:not(:is(:hover, :active))",
            (0, 1, 2),
        ),
        ("div > a.x::before:hover", "div > a.x::before:hover", (0, 2, 3)),
        (r".x::b\65 fore:h\6f ver", ".x::before:hover", (0, 2, 1)),
    ],
)
def test_pseudo_element_state_round_trip(
    source: str, canonical: str, specificity: tuple[int, int, int]
) -> None:
    selector = parse(source)[0]
    assert selector.canonical() == canonical
    assert selector.specificity() == specificity
    reparsed = parse(canonical)[0]
    assert reparsed.canonical() == canonical
    assert reparsed.specificity() == specificity
    assert repr(reparsed) == repr(selector)


@pytest.mark.parametrize(
    "state", ["hover", "active", "focus", "focus-visible", "focus-within"]
)
def test_pseudo_element_state_belongs_to_the_pseudo_element(state: str) -> None:
    selector = parse(f".something::before:{state}")[0]
    pseudo = selector.pseudo_element
    assert isinstance(pseudo, cssselect.QualifiedPseudoElement)
    assert pseudo.pseudo_element == "before"
    assert pseudo.state.canonical() == f"*:{state}"
    assert selector.parsed_tree.canonical() == "*.something"
    document = html.fromstring('<div><p class="something" id="yes"/><p id="no"/></div>')
    xpath = GenericTranslator().selector_to_xpath(selector)
    assert [node.get("id") for node in document.xpath(xpath)] == ["yes"]
    with pytest.raises(ExpressionError, match="Pseudo-elements are not supported"):
        GenericTranslator().selector_to_xpath(selector, translate_pseudo_elements=True)
    with pytest.raises(ExpressionError, match="Pseudo-elements are not supported"):
        GenericTranslator().css_to_xpath(selector.canonical())


def test_pseudo_element_state_keeps_function_arguments() -> None:
    pseudo = parse("a::part(tab):hover")[0].pseudo_element
    assert isinstance(pseudo, cssselect.QualifiedPseudoElement)
    assert isinstance(pseudo.pseudo_element, FunctionalPseudoElement)
    assert pseudo.pseudo_element.name == "part"
    assert [token.value for token in pseudo.pseudo_element.arguments] == ["tab"]


def test_pseudo_element_state_selector_groups() -> None:
    selectors = parse("a::before:hover, b:focus::after, c::part(tab):active")
    assert [selector.canonical() for selector in selectors] == [
        "a::before:hover",
        "b:focus::after",
        "c::part(tab):active",
    ]
    assert [selector.specificity() for selector in selectors] == [
        (0, 1, 2),
        (0, 1, 2),
        (0, 1, 2),
    ]
    assert selectors[1].pseudo_element == "after"


@pytest.mark.parametrize(
    "source",
    [
        "a::before.foo",
        "a::before#id",
        "a::before[title]",
        "a::before:hover.foo",
        "a::before:hover#id",
        "a::before:hover[title]",
        "a::before:hover > b",
        "a::before:hover + b",
        "a::before:hover ~ b",
        "a::before:hover b",
        "a::before:hover :active",
        "a::before::after",
        "a::before:hover::after",
        "a::before:before",
        "a::before:nth-child(1)",
        "a::before:enabled",
        "a::before:unknown",
        "a::before:has(:hover)",
        "a::before:is(.foo)",
        "a::before:is(#id)",
        "a::before:is([title])",
        "a::before:is(*)",
        "a::before:is(*:hover)",
        "a::before:is(a:hover)",
        "a::before:is(:hover, .foo)",
        "a::before:where(:hover, :nth-child(1))",
        "a::before:not(*)",
        "a::before:not(.foo)",
        "a::before:not(:hover > :active)",
        "a::before:not(:hover :active)",
        "a::before:not(:hover, :active)",
        "a::before:is(::after:hover)",
        "a::before:where(:hover,)",
        "a::before:hover(",
        "a::before:",
        "a::before:is()",
        "a::before:not()",
        "a:not(::before:hover)",
        "a:is(::before:hover)",
        "a:has(::before:hover)",
    ],
)
def test_pseudo_element_states_reject_other_selector_kinds(source: str) -> None:
    with pytest.raises(SelectorSyntaxError):
        parse(source)


def test_existing_pseudo_element_representation_is_unchanged() -> None:
    assert parse("a:before")[0].pseudo_element == "before"
    assert parse("a::BEFORE")[0].pseudo_element == "before"
    assert isinstance(parse("a::part(tab)")[0].pseudo_element, FunctionalPseudoElement)
    assert parse("a:hover::before")[0].parsed_tree.canonical() == "a:hover"
