#!/usr/bin/env python
"""
Tests for cssselect
===================

These tests can be run either by py.test or by the standard library's
unittest. They use plain ``assert`` statements and do little reporting
themselves in case of failure.

Use py.test to get fancy error reporting and assert introspection.


:copyright: (c) 2007-2012 Ian Bicking and contributors.
See AUTHORS for more details.
:license: BSD, see LICENSE for more details.

"""

from __future__ import annotations

import sys
import typing
import unittest
from typing import TYPE_CHECKING

from lxml import etree, html

from cssselect import (
    ExpressionError,
    GenericTranslator,
    HTMLTranslator,
    SelectorSyntaxError,
    parse,
)
from cssselect.parser import (
    Function,
    FunctionalPseudoElement,
    PseudoElement,
    Token,
    parse_series,
    tokenize,
)
from cssselect.xpath import XPathExpr

if TYPE_CHECKING:
    from collections.abc import Sequence


class TestCssselect(unittest.TestCase):
    def test_tokenizer(self) -> None:
        tokens = [
            str(item)
            for item in tokenize(r'E\ é > f [a~="y\"x"]:nth(/* fu /]* */-3.7)')
        ]
        assert tokens == [
            "<IDENT 'E é' at 0>",
            "<S ' ' at 4>",
            "<DELIM '>' at 5>",
            "<S ' ' at 6>",
            # the no-break space is not whitespace in CSS
            "<IDENT 'f ' at 7>",  # f\xa0
            "<DELIM '[' at 9>",
            "<IDENT 'a' at 10>",
            "<DELIM '~' at 11>",
            "<DELIM '=' at 12>",
            "<STRING 'y\"x' at 13>",
            "<DELIM ']' at 19>",
            "<DELIM ':' at 20>",
            "<IDENT 'nth' at 21>",
            "<DELIM '(' at 24>",
            "<NUMBER '-3.7' at 37>",
            "<DELIM ')' at 41>",
            "<EOF at 42>",
        ]

    def test_parser(self) -> None:
        def repr_parse(css: str) -> list[str]:
            selectors = parse(css)
            for selector in selectors:
                assert selector.pseudo_element is None
            return [repr(selector.parsed_tree) for selector in selectors]

        def parse_many(first: str, *others: str) -> list[str]:
            result = repr_parse(first)
            for other in others:
                assert repr_parse(other) == result
            return result

        assert parse_many("*") == ["Element[*]"]
        assert parse_many("*|*") == ["Element[*]"]
        assert parse_many("*|foo") == ["Element[foo]"]
        assert parse_many("|foo") == ["Element[foo]"]
        assert parse_many("foo|*") == ["Element[foo|*]"]
        assert parse_many("foo|bar") == ["Element[foo|bar]"]
        # This will never match, but it is valid:
        assert parse_many("#foo#bar") == ["Hash[Hash[Element[*]#foo]#bar]"]
        assert parse_many(
            "div>.foo",
            "div> .foo",
            "div >.foo",
            "div > .foo",
            "div \n>  \t \t .foo",
            "div\r>\n\n\n.foo",
            "div\f>\f.foo",
        ) == ["CombinedSelector[Element[div] > Class[Element[*].foo]]"]
        assert parse_many(
            "td.foo,.bar", "td.foo, .bar", "td.foo\t\r\n\f ,\t\r\n\f .bar"
        ) == [
            "Class[Element[td].foo]",
            "Class[Element[*].bar]",
        ]
        assert parse_many("div, td.foo, div.bar span") == [
            "Element[div]",
            "Class[Element[td].foo]",
            "CombinedSelector[Class[Element[div].bar] <followed> Element[span]]",
        ]
        assert parse_many("div > p") == ["CombinedSelector[Element[div] > Element[p]]"]
        assert parse_many("td:first") == ["Pseudo[Element[td]:first]"]
        assert parse_many("td:first") == ["Pseudo[Element[td]:first]"]
        assert parse_many("td :first") == [
            "CombinedSelector[Element[td] <followed> Pseudo[Element[*]:first]]"
        ]
        assert parse_many("td :first") == [
            "CombinedSelector[Element[td] <followed> Pseudo[Element[*]:first]]"
        ]
        assert parse_many("a[name]", "a[ name\t]") == ["Attrib[Element[a][name]]"]
        assert parse_many("a [name]") == [
            "CombinedSelector[Element[a] <followed> Attrib[Element[*][name]]]"
        ]
        assert parse_many('a[rel="include"]', "a[rel = include]") == [
            "Attrib[Element[a][rel = 'include']]"
        ]
        assert parse_many("a[hreflang |= 'en']", "a[hreflang|=en]") == [
            "Attrib[Element[a][hreflang |= 'en']]"
        ]
        assert parse_many("div:nth-child(10)") == [
            "Function[Element[div]:nth-child(['10'])]"
        ]
        assert parse_many(":nth-child(2n+2)") == [
            "Function[Element[*]:nth-child(['2', 'n', '+2'])]"
        ]
        assert parse_many("div:nth-of-type(10)") == [
            "Function[Element[div]:nth-of-type(['10'])]"
        ]
        assert parse_many("div div:nth-of-type(10) .aclass") == [
            "CombinedSelector[CombinedSelector[Element[div] <followed> "
            "Function[Element[div]:nth-of-type(['10'])]] "
            "<followed> Class[Element[*].aclass]]"
        ]
        assert parse_many("label:only") == ["Pseudo[Element[label]:only]"]
        assert parse_many("a:lang(fr)") == ["Function[Element[a]:lang(['fr'])]"]
        assert parse_many('div:contains("foo")') == [
            "Function[Element[div]:contains(['foo'])]"
        ]
        assert parse_many("div#foobar") == ["Hash[Element[div]#foobar]"]
        assert parse_many("div:not(div.foo)") == [
            "Negation[Element[div]:not(Class[Element[div].foo])]"
        ]
        assert parse_many("div:has(div.foo)") == [
            "Relation[Element[div]:has(Selector[Class[Element[div].foo]])]"
        ]
        assert parse_many("div:is(.foo, #bar)") == [
            "Matching[Element[div]:is(Class[Element[*].foo], Hash[Element[*]#bar])]"
        ]
        assert parse_many(":is(:hover, :visited)") == [
            "Matching[Element[*]:is(Pseudo[Element[*]:hover], Pseudo[Element[*]:visited])]"
        ]
        assert parse_many(":where(:hover, :visited)") == [
            "SpecificityAdjustment[Element[*]:where(Pseudo[Element[*]:hover],"
            " Pseudo[Element[*]:visited])]"
        ]
        assert parse_many("td ~ th") == ["CombinedSelector[Element[td] ~ Element[th]]"]
        assert parse_many(":scope > foo") == [
            "CombinedSelector[Pseudo[Element[*]:scope] > Element[foo]]"
        ]
        assert parse_many(" :scope > foo") == [
            "CombinedSelector[Pseudo[Element[*]:scope] > Element[foo]]"
        ]
        assert parse_many(":scope > foo bar > div") == [
            "CombinedSelector[CombinedSelector[CombinedSelector[Pseudo[Element[*]:scope] > "
            "Element[foo]] <followed> Element[bar]] > Element[div]]"
        ]
        assert parse_many(":scope > #foo #bar") == [
            "CombinedSelector[CombinedSelector[Pseudo[Element[*]:scope] > "
            "Hash[Element[*]#foo]] <followed> Hash[Element[*]#bar]]"
        ]

    def test_pseudo_elements(self) -> None:
        def parse_pseudo(css: str) -> list[tuple[str, str | None]]:
            result: list[tuple[str, str | None]] = []
            for selector in parse(css):
                pseudo = selector.pseudo_element
                pseudo = str(pseudo) if pseudo else pseudo
                # No Symbol here
                assert pseudo is None or isinstance(pseudo, str)
                selector_as_str = repr(selector.parsed_tree)
                result.append((selector_as_str, pseudo))
            return result

        def parse_one(css: str) -> tuple[str, str | None]:
            result = parse_pseudo(css)
            assert len(result) == 1
            return result[0]

        def test_pseudo_repr(css: str) -> str:
            result = parse(css)
            assert len(result) == 1
            selector = result[0]
            return repr(selector.parsed_tree)

        assert parse_one("foo") == ("Element[foo]", None)
        assert parse_one("*") == ("Element[*]", None)
        assert parse_one(":empty") == ("Pseudo[Element[*]:empty]", None)
        assert parse_one(":scope") == ("Pseudo[Element[*]:scope]", None)

        # Special cases for CSS 2.1 pseudo-elements
        assert parse_one(":BEfore") == ("Element[*]", "before")
        assert parse_one(":aftER") == ("Element[*]", "after")
        assert parse_one(":First-Line") == ("Element[*]", "first-line")
        assert parse_one(":First-Letter") == ("Element[*]", "first-letter")

        assert parse_one("::befoRE") == ("Element[*]", "before")
        assert parse_one("::AFter") == ("Element[*]", "after")
        assert parse_one("::firsT-linE") == ("Element[*]", "first-line")
        assert parse_one("::firsT-letteR") == ("Element[*]", "first-letter")

        assert parse_one("::text-content") == ("Element[*]", "text-content")
        assert parse_one("::attr(name)") == (
            "Element[*]",
            "FunctionalPseudoElement[::attr(['name'])]",
        )

        assert parse_one("::Selection") == ("Element[*]", "selection")
        assert parse_one("foo:after") == ("Element[foo]", "after")
        assert parse_one("foo::selection") == ("Element[foo]", "selection")
        assert parse_one("lorem#ipsum ~ a#b.c[href]:empty::selection") == (
            "CombinedSelector[Hash[Element[lorem]#ipsum] ~ "
            "Pseudo[Attrib[Class[Hash[Element[a]#b].c][href]]:empty]]",
            "selection",
        )
        assert parse_pseudo(":scope > div, foo bar") == [
            ("CombinedSelector[Pseudo[Element[*]:scope] > Element[div]]", None),
            ("CombinedSelector[Element[foo] <followed> Element[bar]]", None),
        ]
        assert parse_pseudo("foo bar, :scope > div") == [
            ("CombinedSelector[Element[foo] <followed> Element[bar]]", None),
            ("CombinedSelector[Pseudo[Element[*]:scope] > Element[div]]", None),
        ]
        assert parse_pseudo("foo bar,:scope > div") == [
            ("CombinedSelector[Element[foo] <followed> Element[bar]]", None),
            ("CombinedSelector[Pseudo[Element[*]:scope] > Element[div]]", None),
        ]
        assert parse_pseudo("foo:before, bar, baz:after") == [
            ("Element[foo]", "before"),
            ("Element[bar]", None),
            ("Element[baz]", "after"),
        ]

        # Special cases for CSS 2.1 pseudo-elements are ignored by default
        for pseudo in ("after", "before", "first-line", "first-letter"):
            (selector,) = parse(f"e:{pseudo}")
            assert selector.pseudo_element == pseudo
            assert GenericTranslator().selector_to_xpath(selector, prefix="") == "e"

        # Pseudo Elements are ignored by default, but if allowed they are not
        # supported by GenericTranslator
        tr = GenericTranslator()
        (selector,) = parse("e::foo")
        assert selector.pseudo_element == "foo"
        assert tr.selector_to_xpath(selector, prefix="") == "e"
        self.assertRaises(
            ExpressionError,
            tr.selector_to_xpath,
            selector,
            translate_pseudo_elements=True,
        )

        # Special test for the unicode symbols and ':scope' element if check
        # Errors if use repr() instead of __repr__()
        assert test_pseudo_repr(":fİrst-child") == "Pseudo[Element[*]:fİrst-child]"
        assert test_pseudo_repr(":scope") == "Pseudo[Element[*]:scope]"

    def test_specificity(self) -> None:
        def specificity(css: str) -> tuple[int, int, int]:
            selectors = parse(css)
            assert len(selectors) == 1
            return selectors[0].specificity()

        assert specificity("*") == (0, 0, 0)
        assert specificity(" foo") == (0, 0, 1)
        assert specificity(":empty ") == (0, 1, 0)
        assert specificity(":before") == (0, 0, 1)
        assert specificity("*:before") == (0, 0, 1)
        assert specificity(":nth-child(2)") == (0, 1, 0)
        assert specificity(".bar") == (0, 1, 0)
        assert specificity("[baz]") == (0, 1, 0)
        assert specificity('[baz="4"]') == (0, 1, 0)
        assert specificity('[baz^="4"]') == (0, 1, 0)
        assert specificity("#lipsum") == (1, 0, 0)
        assert specificity("::attr(name)") == (0, 0, 1)

        assert specificity(":not(*)") == (0, 0, 0)
        assert specificity(":not(foo)") == (0, 0, 1)
        assert specificity(":not(.foo)") == (0, 1, 0)
        assert specificity(":not([foo])") == (0, 1, 0)
        assert specificity(":not(:empty)") == (0, 1, 0)
        assert specificity(":not(#foo)") == (1, 0, 0)

        assert specificity(":has(*)") == (0, 0, 0)
        assert specificity(":has(foo)") == (0, 0, 1)
        assert specificity(":has(.foo)") == (0, 1, 0)
        assert specificity(":has(> foo)") == (0, 0, 1)

        assert specificity(":is(.foo, #bar)") == (1, 0, 0)
        assert specificity(":is(:hover, :visited)") == (0, 1, 0)
        assert specificity(":where(:hover, :visited)") == (0, 0, 0)

        assert specificity("foo:empty") == (0, 1, 1)
        assert specificity("foo:before") == (0, 0, 2)
        assert specificity("foo::before") == (0, 0, 2)
        assert specificity("foo:empty::before") == (0, 1, 2)

        assert specificity("#lorem + foo#ipsum:first-child > bar:first-line") == (
            2,
            1,
            3,
        )

    def test_css_export(self) -> None:
        def css2css(css: str, res: str | None = None) -> None:
            selectors = parse(css)
            assert len(selectors) == 1
            assert selectors[0].canonical() == (res or css)

        css2css("*")
        css2css(" foo", "foo")
        css2css("Foo", "Foo")
        css2css(":empty ", ":empty")
        css2css(":before", "::before")
        css2css(":beFOre", "::before")
        css2css("*:before", "::before")
        css2css(":nth-child(2)")
        css2css(".bar")
        css2css("[baz]")
        css2css('[baz="4"]', "[baz='4']")
        css2css('[baz^="4"]', "[baz^='4']")
        css2css("[ns|attr='4']")
        css2css("#lipsum")
        css2css(":not(*)")
        css2css(":not(foo)")
        css2css(":not(*.foo)", ":not(.foo)")
        css2css(":not(*[foo])", ":not([foo])")
        css2css(":not(:empty)")
        css2css(":not(#foo)")
        css2css(":has(*)")
        css2css(":has(foo)")
        css2css(":has(*.foo)", ":has(.foo)")
        css2css(":is(#bar, .foo)")
        css2css(":is(:focused, :visited)")
        css2css(":where(:focused, :visited)")
        css2css("foo:empty")
        css2css("foo::before")
        css2css("foo:empty::before")
        css2css('::name(arg + "val" - 3)', "::name(arg+'val'-3)")
        css2css("#lorem + foo#ipsum:first-child > bar::first-line")
        css2css("foo > *")

    def test_parse_errors(self) -> None:
        def get_error(css: str) -> str | None:
            try:
                parse(css)
            except SelectorSyntaxError:
                return str(sys.exc_info()[1])
            return None

        assert get_error("attributes(href)/html/body/a") == (
            "Expected selector, got <DELIM '(' at 10>"
        )
        assert get_error("attributes(href)") == (
            "Expected selector, got <DELIM '(' at 10>"
        )
        assert get_error("html/body/a") == ("Expected selector, got <DELIM '/' at 4>")
        assert get_error(" ") == ("Expected selector, got <EOF at 1>")
        assert get_error("div, ") == ("Expected selector, got <EOF at 5>")
        assert get_error(" , div") == ("Expected selector, got <DELIM ',' at 1>")
        assert get_error("p, , div") == ("Expected selector, got <DELIM ',' at 3>")
        assert get_error("div > ") == ("Expected selector, got <EOF at 6>")
        assert get_error("  > div") == ("Expected selector, got <DELIM '>' at 2>")
        assert get_error("foo|#bar") == ("Expected ident or '*', got <HASH 'bar' at 4>")
        assert get_error("#.foo") == ("Expected selector, got <DELIM '#' at 0>")
        assert get_error(".#foo") == ("Expected ident, got <HASH 'foo' at 1>")
        assert get_error(":#foo") == ("Expected ident, got <HASH 'foo' at 1>")
        assert get_error("[*]") == ("Expected '|', got <DELIM ']' at 2>")
        assert get_error("[foo|]") == ("Expected ident, got <DELIM ']' at 5>")
        assert get_error("[#]") == ("Expected ident or '*', got <DELIM '#' at 1>")
        assert get_error("[foo=#]") == (
            "Expected string or ident, got <DELIM '#' at 5>"
        )
        assert get_error("[href]a") == ("Expected selector, got <IDENT 'a' at 6>")
        assert get_error("[rel=stylesheet]") is None
        assert get_error("[rel:stylesheet]") == (
            "Operator expected, got <DELIM ':' at 4>"
        )
        assert get_error("[rel=stylesheet") == ("Expected ']', got <EOF at 15>")
        assert get_error(":lang(fr)") is None
        assert get_error(":lang(fr") == ("Expected an argument, got <EOF at 8>")
        assert get_error(':contains("foo') == ("Unclosed string at 10")
        assert get_error("foo!") == ("Expected selector, got <DELIM '!' at 3>")

        # Mis-placed pseudo-elements
        assert get_error("a:before:empty") == (
            "Got pseudo-element ::before not at the end of a selector"
        )
        assert get_error("li:before a") == (
            "Got pseudo-element ::before not at the end of a selector"
        )
        assert get_error(":not(:before)") == (
            "Got pseudo-element ::before inside :not() at 12"
        )
        assert get_error(":not(:not(a))") == ("Got nested :not()")
        assert get_error(":is(:before)") == (
            "Got pseudo-element ::before inside function"
        )
        assert get_error(":is(a b)") == ("Expected an argument, got <IDENT 'b' at 6>")
        assert get_error(":where(:before)") == (
            "Got pseudo-element ::before inside function"
        )
        assert get_error(":where(a b)") == (
            "Expected an argument, got <IDENT 'b' at 9>"
        )
        assert get_error(":scope > div :scope header") == (
            'Got immediate child pseudo-element ":scope" not at the start of a selector'
        )
        assert get_error("div :scope header") == (
            'Got immediate child pseudo-element ":scope" not at the start of a selector'
        )
        assert get_error("> div p") == ("Expected selector, got <DELIM '>' at 0>")

        # Unsupported :has() with several arguments
        assert get_error(":has(a, b)") == ("Expected an argument, got <DELIM ',' at 6>")
        assert get_error(":has()") == ("Expected selector, got <EOF at 0>")

    def test_translation(self) -> None:
        def xpath(css: str) -> str:
            return str(GenericTranslator().css_to_xpath(css, prefix=""))

        assert xpath("*") == "*"
        assert xpath("e") == "e"
        assert xpath("*|e") == "e"
        assert xpath("e|f") == "e:f"
        assert xpath("e[foo]") == "e[@foo]"
        assert xpath("e[foo|bar]") == "e[@foo:bar]"
        assert xpath('e[foo="bar"]') == "e[@foo = 'bar']"
        assert xpath('e[foo~="bar"]') == (
            "e[@foo and contains(concat(' ', normalize-space(@foo), ' '), ' bar ')]"
        )
        assert xpath('e[foo^="bar"]') == ("e[@foo and starts-with(@foo, 'bar')]")
        assert xpath('e[foo$="bar"]') == (
            "e[@foo and substring(@foo, string-length(@foo)-2) = 'bar']"
        )
        assert xpath('e[foo*="bar"]') == ("e[@foo and contains(@foo, 'bar')]")
        assert xpath('e[hreflang|="en"]') == (
            "e[@hreflang and (@hreflang = 'en' or starts-with(@hreflang, 'en-'))]"
        )

        # --- nth-* and nth-last-* -------------------------------------
        assert xpath("e:nth-child(1)") == ("e[count(preceding-sibling::*) = 0]")

        # always true
        assert xpath("e:nth-child(n)") == ("e")
        assert xpath("e:nth-child(n+1)") == ("e")
        # always true too
        assert xpath("e:nth-child(n-10)") == ("e")
        # b=2 is the limit...
        assert xpath("e:nth-child(n+2)") == ("e[count(preceding-sibling::*) >= 1]")
        # always false
        assert xpath("e:nth-child(-n)") == ("e[0]")
        # equivalent to first child
        assert xpath("e:nth-child(-n+1)") == ("e[count(preceding-sibling::*) <= 0]")

        assert xpath("e:nth-child(3n+2)") == (
            "e[(count(preceding-sibling::*) >= 1) and "
            "((count(preceding-sibling::*) +2) mod 3 = 0)]"
        )
        assert xpath("e:nth-child(3n-2)") == (
            "e[count(preceding-sibling::*) mod 3 = 0]"
        )
        assert xpath("e:nth-child(-n+6)") == ("e[count(preceding-sibling::*) <= 5]")

        assert xpath("e:nth-last-child(1)") == ("e[count(following-sibling::*) = 0]")
        assert xpath("e:nth-last-child(2n)") == (
            "e[(count(following-sibling::*) +1) mod 2 = 0]"
        )
        assert xpath("e:nth-last-child(2n+1)") == (
            "e[count(following-sibling::*) mod 2 = 0]"
        )
        assert xpath("e:nth-last-child(2n+2)") == (
            "e[(count(following-sibling::*) >= 1) and "
            "((count(following-sibling::*) +1) mod 2 = 0)]"
        )
        assert xpath("e:nth-last-child(3n+1)") == (
            "e[count(following-sibling::*) mod 3 = 0]"
        )
        # represents the two last e elements
        assert xpath("e:nth-last-child(-n+2)") == (
            "e[count(following-sibling::*) <= 1]"
        )

        assert xpath("e:nth-of-type(1)") == ("e[count(preceding-sibling::e) = 0]")
        assert xpath("e:nth-last-of-type(1)") == ("e[count(following-sibling::e) = 0]")
        assert xpath("div e:nth-last-of-type(1) .aclass") == (
            "div/descendant-or-self::*/e[count(following-sibling::e) = 0]"
            "/descendant-or-self::*/*[@class and contains("
            "concat(' ', normalize-space(@class), ' '), ' aclass ')]"
        )

        assert xpath("e:first-child") == ("e[count(preceding-sibling::*) = 0]")
        assert xpath("e:last-child") == ("e[count(following-sibling::*) = 0]")
        assert xpath("e:first-of-type") == ("e[count(preceding-sibling::e) = 0]")
        assert xpath("e:last-of-type") == ("e[count(following-sibling::e) = 0]")
        assert xpath("e:only-child") == ("e[count(parent::*/child::*) = 1]")
        assert xpath("e:only-of-type") == ("e[count(parent::*/child::e) = 1]")
        assert xpath("e:empty") == ("e[not(*) and not(string-length())]")
        assert xpath("e:EmPTY") == ("e[not(*) and not(string-length())]")
        assert xpath("e:root") == ("e[not(parent::*)]")
        assert xpath("e:hover") == ("e[0]")  # never matches
        assert (
            xpath("div:has(bar.foo)") == "div[descendant::bar"
            "[@class and contains(concat(' ', normalize-space(@class), ' '), ' foo ')]]"
        )
        assert xpath("e:has(> f)") == "e[./f]"
        assert xpath("e:has(f)") == "e[descendant::f]"
        assert xpath("e:has(~ f)") == "e[following-sibling::f]"
        assert (
            xpath("e:has(+ f)")
            == "e[following-sibling::*[(name() = 'f') and (position() = 1)]]"
        )
        assert xpath('e:contains("foo")') == ("e[contains(., 'foo')]")
        assert xpath("e:ConTains(foo)") == ("e[contains(., 'foo')]")
        assert xpath("e.warning") == (
            "e[@class and contains("
            "concat(' ', normalize-space(@class), ' '), ' warning ')]"
        )
        assert xpath("e#myid") == ("e[@id = 'myid']")
        assert xpath("e:not(:nth-child(odd))") == (
            "e[not(count(preceding-sibling::*) mod 2 = 0)]"
        )
        assert xpath("e:nOT(*)") == ("e[0]")  # never matches
        assert xpath("e f") == ("e/descendant-or-self::*/f")
        assert xpath("e > f") == ("e/f")
        assert xpath("e + f") == (
            "e/following-sibling::*[(name() = 'f') and (position() = 1)]"
        )
        assert xpath("e ~ f") == ("e/following-sibling::f")
        assert xpath("e ~ f:nth-child(3)") == (
            "e/following-sibling::f[count(preceding-sibling::*) = 2]"
        )
        assert xpath("div#container p") == (
            "div[@id = 'container']/descendant-or-self::*/p"
        )
        assert xpath("e:where(foo)") == "e[name() = 'foo']"
        assert xpath("e:where(foo, bar)") == "e[(name() = 'foo') or (name() = 'bar')]"

        # Invalid characters in XPath element names
        assert xpath(r"di\a0 v") == ("*[name() = 'di v']")  # di\xa0v
        assert xpath(r"di\[v") == ("*[name() = 'di[v']")
        assert xpath(r"[h\a0 ref]") == ("*[attribute::*[name() = 'h ref']]")  # h\xa0ref
        assert xpath(r"[h\]ref]") == ("*[attribute::*[name() = 'h]ref']]")

        self.assertRaises(ExpressionError, xpath, ":fİrst-child")
        self.assertRaises(ExpressionError, xpath, ":first-of-type")
        self.assertRaises(ExpressionError, xpath, ":only-of-type")
        self.assertRaises(ExpressionError, xpath, ":last-of-type")
        self.assertRaises(ExpressionError, xpath, ":nth-of-type(1)")
        self.assertRaises(ExpressionError, xpath, ":nth-last-of-type(1)")
        self.assertRaises(ExpressionError, xpath, ":nth-child(n-)")
        self.assertRaises(ExpressionError, xpath, ":after")
        self.assertRaises(ExpressionError, xpath, ":lorem-ipsum")
        self.assertRaises(ExpressionError, xpath, ":lorem(ipsum)")
        self.assertRaises(ExpressionError, xpath, "::lorem-ipsum")
        self.assertRaises(TypeError, GenericTranslator().css_to_xpath, 4)
        self.assertRaises(TypeError, GenericTranslator().selector_to_xpath, "foo")

    def test_unicode(self) -> None:
        css = ".a\xc1b"
        xpath = GenericTranslator().css_to_xpath(css)
        assert css[1:] in xpath
        xpath = xpath.encode("ascii", "xmlcharrefreplace").decode("ASCII")
        assert xpath == (
            "descendant-or-self::*[@class and contains("
            "concat(' ', normalize-space(@class), ' '), ' a&#193;b ')]"
        )

    def test_quoting(self) -> None:
        css_to_xpath = GenericTranslator().css_to_xpath
        assert css_to_xpath('*[aval="\'"]') == (
            """descendant-or-self::*[@aval = "'"]"""
        )
        assert css_to_xpath("*[aval=\"'''\"]") == (
            """descendant-or-self::*[@aval = "'''"]"""
        )
        assert css_to_xpath("*[aval='\"']") == (
            """descendant-or-self::*[@aval = '"']"""
        )
        assert css_to_xpath('*[aval=\'"""\']') == (
            '''descendant-or-self::*[@aval = '"""']'''
        )
        assert css_to_xpath(':scope > div[dataimg="<testmessage>"]') == (
            "descendant-or-self::*[1]/div[@dataimg = '<testmessage>']"
        )

    def test_unicode_escapes(self) -> None:
        # \22 == '"'  \20 == ' '
        css_to_xpath = GenericTranslator().css_to_xpath
        assert css_to_xpath(r'*[aval="\'\22\'"]') == (
            """descendant-or-self::*[@aval = concat("'",'"',"'")]"""
        )
        assert css_to_xpath(r'*[aval="\'\22 2\'"]') == (
            """descendant-or-self::*[@aval = concat("'",'"2',"'")]"""
        )
        assert css_to_xpath(r'*[aval="\'\20  \'"]') == (
            """descendant-or-self::*[@aval = "'  '"]"""
        )
        assert css_to_xpath("*[aval=\"'\\20\r\n '\"]") == (
            """descendant-or-self::*[@aval = "'  '"]"""
        )

    def test_xpath_pseudo_elements(self) -> None:
        class CustomTranslator(GenericTranslator):
            def xpath_pseudo_element(
                self, xpath: XPathExpr, pseudo_element: PseudoElement
            ) -> XPathExpr:
                if isinstance(pseudo_element, FunctionalPseudoElement):
                    method_name = "xpath_{}_functional_pseudo_element".format(
                        pseudo_element.name.replace("-", "_")
                    )
                    method = getattr(self, method_name, None)
                    if not method:
                        raise ExpressionError(
                            f"The functional pseudo-element ::{pseudo_element.name}() is unknown"
                        )
                    xpath = method(xpath, pseudo_element.arguments)
                else:
                    method_name = "xpath_{}_simple_pseudo_element".format(
                        pseudo_element.replace("-", "_")
                    )
                    method = getattr(self, method_name, None)
                    if not method:
                        raise ExpressionError(
                            f"The pseudo-element ::{pseudo_element} is unknown"
                        )
                    xpath = method(xpath)
                return xpath

            # functional pseudo-class:
            # elements that have a certain number of attributes
            def xpath_nb_attr_function(
                self, xpath: XPathExpr, function: Function
            ) -> XPathExpr:
                assert function.arguments[0].value
                nb_attributes = int(function.arguments[0].value)
                return xpath.add_condition(f"count(@*)={nb_attributes}")

            # pseudo-class:
            # elements that have 5 attributes
            def xpath_five_attributes_pseudo(self, xpath: XPathExpr) -> XPathExpr:
                return xpath.add_condition("count(@*)=5")

            # functional pseudo-element:
            # element's attribute by name
            def xpath_attr_functional_pseudo_element(
                self, xpath: XPathExpr, arguments: Sequence[Token]
            ) -> XPathExpr:
                attribute_name = arguments[0].value
                other = XPathExpr(
                    f"@{attribute_name}",
                    "",
                )
                return xpath.join("/", other)

            # pseudo-element:
            # element's text() nodes
            def xpath_text_node_simple_pseudo_element(
                self, xpath: XPathExpr
            ) -> XPathExpr:
                other = XPathExpr(
                    "text()",
                    "",
                )
                return xpath.join("/", other)

            # pseudo-element:
            # element's href attribute
            def xpath_attr_href_simple_pseudo_element(
                self, xpath: XPathExpr
            ) -> XPathExpr:
                other = XPathExpr(
                    "@href",
                    "",
                )
                return xpath.join("/", other)

            # pseudo-element:
            # used to demonstrate operator precedence
            def xpath_first_or_second_pseudo(self, xpath: XPathExpr) -> XPathExpr:
                return xpath.add_condition("@id = 'first' or @id = 'second'")

        def xpath(css: str) -> str:
            return str(CustomTranslator().css_to_xpath(css))

        assert xpath(":five-attributes") == "descendant-or-self::*[count(@*)=5]"
        assert xpath(":nb-attr(3)") == "descendant-or-self::*[count(@*)=3]"
        assert xpath("::attr(href)") == "descendant-or-self::*/@href"
        assert xpath("::text-node") == "descendant-or-self::*/text()"
        assert xpath("::attr-href") == "descendant-or-self::*/@href"
        assert xpath("p img::attr(src)") == (
            "descendant-or-self::p/descendant-or-self::*/img/@src"
        )
        assert xpath(":scope") == "descendant-or-self::*[1]"
        assert xpath(":first-or-second[href]") == (
            "descendant-or-self::*[(@id = 'first' or @id = 'second') and (@href)]"
        )

        assert str(XPathExpr("", "", condition="@href")) == "[@href]"

        document = etree.fromstring(OPERATOR_PRECEDENCE_IDS)
        sort_key = {el: count for count, el in enumerate(document.iter())}.__getitem__

        def operator_id(selector: str) -> list[str]:
            xpath = CustomTranslator().css_to_xpath(selector)
            items = typing.cast(list["etree._Element"], document.xpath(xpath))
            items.sort(key=sort_key)
            return [element.get("id", "nil") for element in items]

        assert operator_id(":first-or-second") == ["first", "second"]
        assert operator_id(":first-or-second[href]") == ["second"]
        assert operator_id("[href]:first-or-second") == ["second"]

    def test_series(self) -> None:
        def series(css: str) -> tuple[int, int] | None:
            (selector,) = parse(f":nth-child({css})")
            args = typing.cast(FunctionalPseudoElement, selector.parsed_tree).arguments
            try:
                return parse_series(args)
            except ValueError:
                return None

        assert series("1n+3") == (1, 3)
        assert series("1n +3") == (1, 3)
        assert series("1n + 3") == (1, 3)
        assert series("1n+ 3") == (1, 3)
        assert series("1n-3") == (1, -3)
        assert series("1n -3") == (1, -3)
        assert series("1n - 3") == (1, -3)
        assert series("1n- 3") == (1, -3)
        assert series("n-5") == (1, -5)
        assert series("odd") == (2, 1)
        assert series("even") == (2, 0)
        assert series("3n") == (3, 0)
        assert series("n") == (1, 0)
        assert series("+n") == (1, 0)
        assert series("-n") == (-1, 0)
        assert series("5") == (0, 5)
        assert series("foo") is None
        assert series("n+") is None

    def test_lang(self) -> None:
        document = etree.fromstring(XMLLANG_IDS)
        sort_key = {el: count for count, el in enumerate(document.iter())}.__getitem__
        css_to_xpath = GenericTranslator().css_to_xpath

        def langid(selector: str) -> list[str]:
            xpath = css_to_xpath(selector)
            items = typing.cast(list["etree._Element"], document.xpath(xpath))
            items.sort(key=sort_key)
            return [element.get("id", "nil") for element in items]

        assert langid(':lang("EN")') == ["first", "second", "third", "fourth"]
        assert langid(':lang("en-us")') == ["second", "fourth"]
        assert langid(":lang(en-nz)") == ["third"]
        assert langid(":lang(fr)") == ["fifth"]
        assert langid(":lang(ru)") == ["sixth"]
        assert langid(":lang('ZH')") == ["eighth"]
        assert langid(":lang(de) :lang(zh)") == ["eighth"]
        assert langid(":lang(en), :lang(zh)") == [
            "first",
            "second",
            "third",
            "fourth",
            "eighth",
        ]
        assert langid(":lang(es)") == []

    def test_argument_types(self) -> None:
        class CustomTranslator(GenericTranslator):
            def __init__(self) -> None:
                self.argument_types: list[str] = []

            def xpath_pseudo_element(
                self, xpath: XPathExpr, pseudo_element: PseudoElement
            ) -> XPathExpr:
                self.argument_types += typing.cast(
                    FunctionalPseudoElement, pseudo_element
                ).argument_types()
                return xpath

        def argument_types(css: str) -> list[str]:
            translator = CustomTranslator()
            translator.css_to_xpath(css)
            return translator.argument_types

        mappings: list[tuple[str, list[str]]] = [
            ("", []),
            ("ident", ["IDENT"]),
            ('"string"', ["STRING"]),
            ("1", ["NUMBER"]),
        ]
        for argument_string, argument_list in mappings:
            css = f"::pseudo_element({argument_string})"
            assert argument_types(css) == argument_list

    def test_select(self) -> None:
        document = etree.fromstring(HTML_IDS)
        sort_key = {el: count for count, el in enumerate(document.iter())}.__getitem__
        css_to_xpath = GenericTranslator().css_to_xpath
        html_css_to_xpath = HTMLTranslator().css_to_xpath

        def select_ids(selector: str, html_only: bool) -> list[str]:
            xpath = css_to_xpath(selector)
            items = typing.cast(list["etree._Element"], document.xpath(xpath))
            if html_only:
                assert items == []
                xpath = html_css_to_xpath(selector)
                items = typing.cast(list["etree._Element"], document.xpath(xpath))
            items.sort(key=sort_key)
            return [element.get("id", "nil") for element in items]

        def pcss(main: str, *selectors: str, **kwargs: bool) -> list[str]:
            html_only = kwargs.pop("html_only", False)
            result = select_ids(main, html_only)
            for selector in selectors:
                assert select_ids(selector, html_only) == result
            return result

        all_ids = pcss("*")
        assert all_ids[:6] == [
            "html",
            "nil",
            "link-href",
            "link-nohref",
            "nil",
            "outer-div",
        ]
        assert all_ids[-1:] == ["foobar-span"]
        assert pcss("div") == ["outer-div", "li-div", "foobar-div"]
        assert pcss("DIV", html_only=True) == [
            "outer-div",
            "li-div",
            "foobar-div",
        ]  # case-insensitive in HTML
        assert pcss("div div") == ["li-div"]
        assert pcss("div, div div") == ["outer-div", "li-div", "foobar-div"]
        assert pcss("a[name]") == ["name-anchor"]
        assert pcss("a[NAme]", html_only=True) == [
            "name-anchor"
        ]  # case-insensitive in HTML:
        assert pcss("a[rel]") == ["tag-anchor", "nofollow-anchor"]
        assert pcss('a[rel="tag"]') == ["tag-anchor"]
        assert pcss('a[href*="localhost"]') == ["tag-anchor"]
        assert pcss('a[href*=""]') == []
        assert pcss('a[href^="http"]') == ["tag-anchor", "nofollow-anchor"]
        assert pcss('a[href^="http:"]') == ["tag-anchor"]
        assert pcss('a[href^=""]') == []
        assert pcss('a[href$="org"]') == ["nofollow-anchor"]
        assert pcss('a[href$=""]') == []
        assert pcss('div[foobar~="bc"]', 'div[foobar~="cde"]') == ["foobar-div"]
        assert pcss('[foobar~="ab bc"]', '[foobar~=""]', '[foobar~=" \t"]') == []
        assert pcss('div[foobar~="cd"]') == []
        assert pcss('*[lang|="En"]', '[lang|="En-us"]') == ["second-li"]
        # Attribute values are case sensitive
        assert pcss('*[lang|="en"]', '[lang|="en-US"]') == []
        assert pcss('*[lang|="e"]') == []
        # ... :lang() is not.
        assert pcss(':lang("EN")', "*:lang(en-US)", html_only=True) == [
            "second-li",
            "li-div",
        ]
        assert pcss(':lang("e")', html_only=True) == []
        assert pcss(":scope > div") == []
        assert pcss(":scope body") == ["nil"]
        assert pcss(":scope body > div") == ["outer-div", "foobar-div"]
        assert pcss(":scope head") == ["nil"]
        assert pcss(":scope html") == []

        # --- nth-* and nth-last-* -------------------------------------

        # select nothing
        assert pcss("li:nth-child(-n)") == []
        # select all children
        assert pcss("li:nth-child(n)") == [
            "first-li",
            "second-li",
            "third-li",
            "fourth-li",
            "fifth-li",
            "sixth-li",
            "seventh-li",
        ]

        assert pcss("li:nth-child(3)", "#first-li ~ :nth-child(3)") == ["third-li"]
        assert pcss("li:nth-child(10)") == []
        assert pcss("li:nth-child(2n)", "li:nth-child(even)", "li:nth-child(2n+0)") == [
            "second-li",
            "fourth-li",
            "sixth-li",
        ]
        assert pcss("li:nth-child(+2n+1)", "li:nth-child(odd)") == [
            "first-li",
            "third-li",
            "fifth-li",
            "seventh-li",
        ]
        assert pcss("li:nth-child(2n+4)") == ["fourth-li", "sixth-li"]
        assert pcss("li:nth-child(3n+1)") == ["first-li", "fourth-li", "seventh-li"]
        assert pcss("li:nth-child(-n+3)") == ["first-li", "second-li", "third-li"]
        assert pcss("li:nth-child(-2n+4)") == ["second-li", "fourth-li"]
        assert pcss("li:nth-last-child(0)") == []
        assert pcss("li:nth-last-child(1)") == ["seventh-li"]
        assert pcss("li:nth-last-child(2n)", "li:nth-last-child(even)") == [
            "second-li",
            "fourth-li",
            "sixth-li",
        ]
        assert pcss("li:nth-last-child(2n+1)") == [
            "first-li",
            "third-li",
            "fifth-li",
            "seventh-li",
        ]
        assert pcss("li:nth-last-child(2n+2)") == ["second-li", "fourth-li", "sixth-li"]
        assert pcss("li:nth-last-child(3n+1)") == [
            "first-li",
            "fourth-li",
            "seventh-li",
        ]
        assert pcss("ol:first-of-type") == ["first-ol"]
        assert pcss("ol:nth-child(1)") == []
        assert pcss("ol:nth-of-type(2)") == ["second-ol"]
        assert pcss("ol:nth-last-of-type(1)") == ["second-ol"]

        # "+" and "~" tests
        assert pcss("ol#first-ol li + li:nth-child(4)") == ["fourth-li"]
        assert pcss("li + li:nth-child(1)") == []
        assert pcss("li ~ li:nth-child(2n+1)") == [
            "third-li",
            "fifth-li",
            "seventh-li",
        ]  # all but the first
        assert pcss("li ~ li:nth-last-child(2n+1)") == [
            "third-li",
            "fifth-li",
            "seventh-li",
        ]  # all but the first

        assert pcss("span:only-child") == ["foobar-span"]
        assert pcss("li div:only-child") == ["li-div"]
        assert pcss("div *:only-child") == ["li-div", "foobar-span"]
        self.assertRaises(ExpressionError, pcss, "p *:only-of-type")
        assert pcss("p:only-of-type") == ["paragraph"]
        assert pcss("a:empty", "a:EMpty") == ["name-anchor"]
        assert pcss("li:empty") == ["third-li", "fourth-li", "fifth-li", "sixth-li"]
        assert pcss(":root", "html:root") == ["html"]
        assert pcss("li:root", "* :root") == []
        assert pcss('*:contains("link")', ':CONtains("link")') == [
            "html",
            "nil",
            "outer-div",
            "tag-anchor",
            "nofollow-anchor",
        ]
        assert pcss('*:contains("LInk")') == []  # case sensitive
        assert pcss('*:contains("e")') == [
            "html",
            "nil",
            "outer-div",
            "first-ol",
            "first-li",
            "paragraph",
            "p-em",
        ]
        assert pcss('*:contains("E")') == []  # case-sensitive
        assert pcss(".a", ".b", "*.a", "ol.a") == ["first-ol"]
        assert pcss(".c", "*.c") == ["first-ol", "third-li", "fourth-li"]
        assert pcss("ol *.c", "ol li.c", "li ~ li.c", "ol > li.c") == [
            "third-li",
            "fourth-li",
        ]
        assert pcss("#first-li", "li#first-li", "*#first-li") == ["first-li"]
        assert pcss("li div", "li > div", "div div") == ["li-div"]
        assert pcss("div > div") == []
        assert pcss("div>.c", "div > .c") == ["first-ol"]
        assert pcss("div + div") == ["foobar-div"]
        assert pcss("a ~ a") == ["tag-anchor", "nofollow-anchor"]
        assert pcss('a[rel="tag"] ~ a') == ["nofollow-anchor"]
        assert pcss("ol#first-ol li:last-child") == ["seventh-li"]
        assert pcss("ol#first-ol *:last-child") == ["li-div", "seventh-li"]
        assert pcss("#outer-div:first-child") == ["outer-div"]
        assert pcss("#outer-div :first-child") == [
            "name-anchor",
            "first-li",
            "li-div",
            "p-b",
            "checkbox-fieldset-disabled",
            "area-href",
        ]
        assert pcss("a[href]") == ["tag-anchor", "nofollow-anchor"]
        assert pcss(":not(*)") == []
        assert pcss("a:not([href])") == ["name-anchor"]
        assert pcss("ol :Not(li[class])") == [
            "first-li",
            "second-li",
            "li-div",
            "fifth-li",
            "sixth-li",
            "seventh-li",
        ]
        assert pcss("link:has(*)") == []
        assert pcss("ol:has(div)") == ["first-ol"]
        assert pcss(":is(#first-li, #second-li)") == ["first-li", "second-li"]
        assert pcss("a:is(#name-anchor, #tag-anchor)") == ["name-anchor", "tag-anchor"]
        assert pcss(":is(.c)") == ["first-ol", "third-li", "fourth-li"]
        assert pcss("ol.a.b.c > li.c:nth-child(3)") == ["third-li"]

        # Invalid characters in XPath element names, should not crash
        assert pcss(r"di\a0 v", r"div\[") == []
        assert pcss(r"[h\a0 ref]", r"[h\]ref]") == []

        # HTML-specific
        assert pcss(":link", html_only=True) == [
            "link-href",
            "tag-anchor",
            "nofollow-anchor",
            "area-href",
        ]
        assert pcss(":visited", html_only=True) == []
        assert pcss(":enabled", html_only=True) == [
            "link-href",
            "tag-anchor",
            "nofollow-anchor",
            "checkbox-unchecked",
            "text-checked",
            "checkbox-checked",
            "area-href",
        ]
        assert pcss(":disabled", html_only=True) == [
            "checkbox-disabled",
            "checkbox-disabled-checked",
            "fieldset",
            "checkbox-fieldset-disabled",
        ]
        assert pcss(":checked", html_only=True) == [
            "checkbox-checked",
            "checkbox-disabled-checked",
        ]

    def test_select_shakespeare(self) -> None:
        document = html.document_fromstring(HTML_SHAKESPEARE)
        body = typing.cast(list["etree._Element"], document.xpath("//body"))[0]
        css_to_xpath = GenericTranslator().css_to_xpath

        basestring_ = (str, bytes)

        def count(selector: str) -> int:
            xpath = css_to_xpath(selector)
            results = typing.cast(list["etree._Element"], body.xpath(xpath))
            assert not isinstance(results, basestring_)
            found = set()
            for item in results:
                assert item not in found
                found.add(item)
                assert not isinstance(item, basestring_)
            return len(results)

        # Data borrowed from http://mootools.net/slickspeed/

        ## Changed from original; probably because I'm only
        ## searching the body.
        # assert count('*') == 252
        assert count("*") == 246
        assert count("div:contains(CELIA)") == 26
        assert count("div:only-child") == 22  # ?
        assert count("div:nth-child(even)") == 106
        assert count("div:nth-child(2n)") == 106
        assert count("div:nth-child(odd)") == 137
        assert count("div:nth-child(2n+1)") == 137
        assert count("div:nth-child(n)") == 243
        assert count("div:last-child") == 53
        assert count("div:first-child") == 51
        assert count("div > div") == 242
        assert count("div + div") == 190
        assert count("div ~ div") == 190
        assert count("body") == 1
        assert count("body div") == 243
        assert count("div") == 243
        assert count("div div") == 242
        assert count("div div div") == 241
        assert count("div, div, div") == 243
        assert count("div, a, span") == 243
        assert count(".dialog") == 51
        assert count("div.dialog") == 51
        assert count("div .dialog") == 51
        assert count("div.character, div.dialog") == 99
        assert count("div.direction.dialog") == 0
        assert count("div.dialog.direction") == 0
        assert count("div.dialog.scene") == 1
        assert count("div.scene.scene") == 1
        assert count("div.scene .scene") == 0
        assert count("div.direction .dialog ") == 0
        assert count("div .dialog .direction") == 4
        assert count("div.dialog .dialog .direction") == 4
        assert count("#speech5") == 1
        assert count("div#speech5") == 1
        assert count("div #speech5") == 1
        assert count("div.scene div.dialog") == 49
        assert count("div#scene1 div.dialog div") == 142
        assert count("#scene1 #speech1") == 1
        assert count("div[class]") == 103
        assert count("div[class=dialog]") == 50
        assert count("div[class^=dia]") == 51
        assert count("div[class$=log]") == 50
        assert count("div[class*=sce]") == 1
        assert count("div[class|=dialog]") == 50  # ? Seems right
        assert count("div[class!=madeup]") == 243  # ? Seems right
        assert count("div[class~=dialog]") == 51  # ? Seems right
        assert count(":scope > div") == 1
        assert count(":scope > div > div[class=dialog]") == 1
        assert count(":scope > div div") == 242


OPERATOR_PRECEDENCE_IDS = """
<html>
  <a id="first"></a>
  <a id="second" href="#"></a>
  <a id="third" href="#"></a>
</html>
"""

XMLLANG_IDS = """
<test>
  <a id="first" xml:lang="en">a</a>
  <b id="second" xml:lang="en-US">b</b>
  <c id="third" xml:lang="en-Nz">c</c>
  <d id="fourth" xml:lang="En-us">d</d>
  <e id="fifth" xml:lang="fr">e</e>
  <f id="sixth" xml:lang="ru">f</f>
  <g id="seventh" xml:lang="de">
    <h id="eighth" xml:lang="zh"/>
  </g>
</test>
"""

HTML_IDS = """
<html id="html"><head>
  <link id="link-href" href="foo" />
  <link id="link-nohref" />
</head><body>
<div id="outer-div">
 <a id="name-anchor" name="foo"></a>
 <a id="tag-anchor" rel="tag" href="http://localhost/foo">link</a>
 <a id="nofollow-anchor" rel="nofollow" href="https://example.org">
    link</a>
 <ol id="first-ol" class="a b c">
   <li id="first-li">content</li>
   <li id="second-li" lang="En-us">
     <div id="li-div">
     </div>
   </li>
   <li id="third-li" class="ab c"></li>
   <li id="fourth-li" class="ab
c"></li>
   <li id="fifth-li"></li>
   <li id="sixth-li"></li>
   <li id="seventh-li">  </li>
 </ol>
 <p id="paragraph">
   <b id="p-b">hi</b> <em id="p-em">there</em>
   <b id="p-b2">guy</b>
   <input type="checkbox" id="checkbox-unchecked" />
   <input type="checkbox" id="checkbox-disabled" disabled="" />
   <input type="text" id="text-checked" checked="checked" />
   <input type="hidden" />
   <input type="hidden" disabled="disabled" />
   <input type="checkbox" id="checkbox-checked" checked="checked" />
   <input type="checkbox" id="checkbox-disabled-checked"
          disabled="disabled" checked="checked" />
   <fieldset id="fieldset" disabled="disabled">
     <input type="checkbox" id="checkbox-fieldset-disabled" />
     <input type="hidden" />
   </fieldset>
 </p>
 <ol id="second-ol">
 </ol>
 <map name="dummymap">
   <area shape="circle" coords="200,250,25" href="foo.html" id="area-href" />
   <area shape="default" id="area-nohref" />
 </map>
</div>
<div id="foobar-div" foobar="ab bc
cde"><span id="foobar-span"></span></div>
</body></html>
"""


HTML_SHAKESPEARE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en" debug="true">
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
	<div id="test">
	<div class="dialog">
	<h2>As You Like It</h2>
	<div id="playwright">
	  by William Shakespeare
	</div>
	<div class="dialog scene thirdClass" id="scene1">
	  <h3>ACT I, SCENE III. A room in the palace.</h3>
	  <div class="dialog">
	  <div class="direction">Enter CELIA and ROSALIND</div>
	  </div>
	  <div id="speech1" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.1">Why, cousin! why, Rosalind! Cupid have mercy! not a word?</div>
	  </div>
	  <div id="speech2" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.2">Not one to throw at a dog.</div>
	  </div>
	  <div id="speech3" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.3">No, thy words are too precious to be cast away upon</div>
	  <div id="scene1.3.4">curs; throw some of them at me; come, lame me with reasons.</div>
	  </div>
	  <div id="speech4" class="character">ROSALIND</div>
	  <div id="speech5" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.8">But is all this for your father?</div>
	  </div>
	  <div class="dialog">
	  <div id="scene1.3.5">Then there were two cousins laid up; when the one</div>
	  <div id="scene1.3.6">should be lamed with reasons and the other mad</div>
	  <div id="scene1.3.7">without any.</div>
	  </div>
	  <div id="speech6" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.9">No, some of it is for my child's father. O, how</div>
	  <div id="scene1.3.10">full of briers is this working-day world!</div>
	  </div>
	  <div id="speech7" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.11">They are but burs, cousin, thrown upon thee in</div>
	  <div id="scene1.3.12">holiday foolery: if we walk not in the trodden</div>
	  <div id="scene1.3.13">paths our very petticoats will catch them.</div>
	  </div>
	  <div id="speech8" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.14">I could shake them off my coat: these burs are in my heart.</div>
	  </div>
	  <div id="speech9" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.15">Hem them away.</div>
	  </div>
	  <div id="speech10" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.16">I would try, if I could cry 'hem' and have him.</div>
	  </div>
	  <div id="speech11" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.17">Come, come, wrestle with thy affections.</div>
	  </div>
	  <div id="speech12" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.18">O, they take the part of a better wrestler than myself!</div>
	  </div>
	  <div id="speech13" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.19">O, a good wish upon you! you will try in time, in</div>
	  <div id="scene1.3.20">despite of a fall. But, turning these jests out of</div>
	  <div id="scene1.3.21">service, let us talk in good earnest: is it</div>
	  <div id="scene1.3.22">possible, on such a sudden, you should fall into so</div>
	  <div id="scene1.3.23">strong a liking with old Sir Rowland's youngest son?</div>
	  </div>
	  <div id="speech14" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.24">The duke my father loved his father dearly.</div>
	  </div>
	  <div id="speech15" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.25">Doth it therefore ensue that you should love his son</div>
	  <div id="scene1.3.26">dearly? By this kind of chase, I should hate him,</div>
	  <div id="scene1.3.27">for my father hated his father dearly; yet I hate</div>
	  <div id="scene1.3.28">not Orlando.</div>
	  </div>
	  <div id="speech16" class="character">ROSALIND</div>
	  <div title="wtf" class="dialog">
	  <div id="scene1.3.29">No, faith, hate him not, for my sake.</div>
	  </div>
	  <div id="speech17" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.30">Why should I not? doth he not deserve well?</div>
	  </div>
	  <div id="speech18" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.31">Let me love him for that, and do you love him</div>
	  <div id="scene1.3.32">because I do. Look, here comes the duke.</div>
	  </div>
	  <div id="speech19" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.33">With his eyes full of anger.</div>
	  <div class="direction">Enter DUKE FREDERICK, with Lords</div>
	  </div>
	  <div id="speech20" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.34">Mistress, dispatch you with your safest haste</div>
	  <div id="scene1.3.35">And get you from our court.</div>
	  </div>
	  <div id="speech21" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.36">Me, uncle?</div>
	  </div>
	  <div id="speech22" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.37">You, cousin</div>
	  <div id="scene1.3.38">Within these ten days if that thou be'st found</div>
	  <div id="scene1.3.39">So near our public court as twenty miles,</div>
	  <div id="scene1.3.40">Thou diest for it.</div>
	  </div>
	  <div id="speech23" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.41">                  I do beseech your grace,</div>
	  <div id="scene1.3.42">Let me the knowledge of my fault bear with me:</div>
	  <div id="scene1.3.43">If with myself I hold intelligence</div>
	  <div id="scene1.3.44">Or have acquaintance with mine own desires,</div>
	  <div id="scene1.3.45">If that I do not dream or be not frantic,--</div>
	  <div id="scene1.3.46">As I do trust I am not--then, dear uncle,</div>
	  <div id="scene1.3.47">Never so much as in a thought unborn</div>
	  <div id="scene1.3.48">Did I offend your highness.</div>
	  </div>
	  <div id="speech24" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.49">Thus do all traitors:</div>
	  <div id="scene1.3.50">If their purgation did consist in words,</div>
	  <div id="scene1.3.51">They are as innocent as grace itself:</div>
	  <div id="scene1.3.52">Let it suffice thee that I trust thee not.</div>
	  </div>
	  <div id="speech25" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.53">Yet your mistrust cannot make me a traitor:</div>
	  <div id="scene1.3.54">Tell me whereon the likelihood depends.</div>
	  </div>
	  <div id="speech26" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.55">Thou art thy father's daughter; there's enough.</div>
	  </div>
	  <div id="speech27" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.56">So was I when your highness took his dukedom;</div>
	  <div id="scene1.3.57">So was I when your highness banish'd him:</div>
	  <div id="scene1.3.58">Treason is not inherited, my lord;</div>
	  <div id="scene1.3.59">Or, if we did derive it from our friends,</div>
	  <div id="scene1.3.60">What's that to me? my father was no traitor:</div>
	  <div id="scene1.3.61">Then, good my liege, mistake me not so much</div>
	  <div id="scene1.3.62">To think my poverty is treacherous.</div>
	  </div>
	  <div id="speech28" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.63">Dear sovereign, hear me speak.</div>
	  </div>
	  <div id="speech29" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.64">Ay, Celia; we stay'd her for your sake,</div>
	  <div id="scene1.3.65">Else had she with her father ranged along.</div>
	  </div>
	  <div id="speech30" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.66">I did not then entreat to have her stay;</div>
	  <div id="scene1.3.67">It was your pleasure and your own remorse:</div>
	  <div id="scene1.3.68">I was too young that time to value her;</div>
	  <div id="scene1.3.69">But now I know her: if she be a traitor,</div>
	  <div id="scene1.3.70">Why so am I; we still have slept together,</div>
	  <div id="scene1.3.71">Rose at an instant, learn'd, play'd, eat together,</div>
	  <div id="scene1.3.72">And wheresoever we went, like Juno's swans,</div>
	  <div id="scene1.3.73">Still we went coupled and inseparable.</div>
	  </div>
	  <div id="speech31" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.74">She is too subtle for thee; and her smoothness,</div>
	  <div id="scene1.3.75">Her very silence and her patience</div>
	  <div id="scene1.3.76">Speak to the people, and they pity her.</div>
	  <div id="scene1.3.77">Thou art a fool: she robs thee of thy name;</div>
	  <div id="scene1.3.78">And thou wilt show more bright and seem more virtuous</div>
	  <div id="scene1.3.79">When she is gone. Then open not thy lips:</div>
	  <div id="scene1.3.80">Firm and irrevocable is my doom</div>
	  <div id="scene1.3.81">Which I have pass'd upon her; she is banish'd.</div>
	  </div>
	  <div id="speech32" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.82">Pronounce that sentence then on me, my liege:</div>
	  <div id="scene1.3.83">I cannot live out of her company.</div>
	  </div>
	  <div id="speech33" class="character">DUKE FREDERICK</div>
	  <div class="dialog">
	  <div id="scene1.3.84">You are a fool. You, niece, provide yourself:</div>
	  <div id="scene1.3.85">If you outstay the time, upon mine honour,</div>
	  <div id="scene1.3.86">And in the greatness of my word, you die.</div>
	  <div class="direction">Exeunt DUKE FREDERICK and Lords</div>
	  </div>
	  <div id="speech34" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.87">O my poor Rosalind, whither wilt thou go?</div>
	  <div id="scene1.3.88">Wilt thou change fathers? I will give thee mine.</div>
	  <div id="scene1.3.89">I charge thee, be not thou more grieved than I am.</div>
	  </div>
	  <div id="speech35" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.90">I have more cause.</div>
	  </div>
	  <div id="speech36" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.91">                  Thou hast not, cousin;</div>
	  <div id="scene1.3.92">Prithee be cheerful: know'st thou not, the duke</div>
	  <div id="scene1.3.93">Hath banish'd me, his daughter?</div>
	  </div>
	  <div id="speech37" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.94">That he hath not.</div>
	  </div>
	  <div id="speech38" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.95">No, hath not? Rosalind lacks then the love</div>
	  <div id="scene1.3.96">Which teacheth thee that thou and I am one:</div>
	  <div id="scene1.3.97">Shall we be sunder'd? shall we part, sweet girl?</div>
	  <div id="scene1.3.98">No: let my father seek another heir.</div>
	  <div id="scene1.3.99">Therefore devise with me how we may fly,</div>
	  <div id="scene1.3.100">Whither to go and what to bear with us;</div>
	  <div id="scene1.3.101">And do not seek to take your change upon you,</div>
	  <div id="scene1.3.102">To bear your griefs yourself and leave me out;</div>
	  <div id="scene1.3.103">For, by this heaven, now at our sorrows pale,</div>
	  <div id="scene1.3.104">Say what thou canst, I'll go along with thee.</div>
	  </div>
	  <div id="speech39" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.105">Why, whither shall we go?</div>
	  </div>
	  <div id="speech40" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.106">To seek my uncle in the forest of Arden.</div>
	  </div>
	  <div id="speech41" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.107">Alas, what danger will it be to us,</div>
	  <div id="scene1.3.108">Maids as we are, to travel forth so far!</div>
	  <div id="scene1.3.109">Beauty provoketh thieves sooner than gold.</div>
	  </div>
	  <div id="speech42" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.110">I'll put myself in poor and mean attire</div>
	  <div id="scene1.3.111">And with a kind of umber smirch my face;</div>
	  <div id="scene1.3.112">The like do you: so shall we pass along</div>
	  <div id="scene1.3.113">And never stir assailants.</div>
	  </div>
	  <div id="speech43" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.114">Were it not better,</div>
	  <div id="scene1.3.115">Because that I am more than common tall,</div>
	  <div id="scene1.3.116">That I did suit me all points like a man?</div>
	  <div id="scene1.3.117">A gallant curtle-axe upon my thigh,</div>
	  <div id="scene1.3.118">A boar-spear in my hand; and--in my heart</div>
	  <div id="scene1.3.119">Lie there what hidden woman's fear there will--</div>
	  <div id="scene1.3.120">We'll have a swashing and a martial outside,</div>
	  <div id="scene1.3.121">As many other mannish cowards have</div>
	  <div id="scene1.3.122">That do outface it with their semblances.</div>
	  </div>
	  <div id="speech44" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.123">What shall I call thee when thou art a man?</div>
	  </div>
	  <div id="speech45" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.124">I'll have no worse a name than Jove's own page;</div>
	  <div id="scene1.3.125">And therefore look you call me Ganymede.</div>
	  <div id="scene1.3.126">But what will you be call'd?</div>
	  </div>
	  <div id="speech46" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.127">Something that hath a reference to my state</div>
	  <div id="scene1.3.128">No longer Celia, but Aliena.</div>
	  </div>
	  <div id="speech47" class="character">ROSALIND</div>
	  <div class="dialog">
	  <div id="scene1.3.129">But, cousin, what if we assay'd to steal</div>
	  <div id="scene1.3.130">The clownish fool out of your father's court?</div>
	  <div id="scene1.3.131">Would he not be a comfort to our travel?</div>
	  </div>
	  <div id="speech48" class="character">CELIA</div>
	  <div class="dialog">
	  <div id="scene1.3.132">He'll go along o'er the wide world with me;</div>
	  <div id="scene1.3.133">Leave me alone to woo him. Let's away,</div>
	  <div id="scene1.3.134">And get our jewels and our wealth together,</div>
	  <div id="scene1.3.135">Devise the fittest time and safest way</div>
	  <div id="scene1.3.136">To hide us from pursuit that will be made</div>
	  <div id="scene1.3.137">After my flight. Now go we in content</div>
	  <div id="scene1.3.138">To liberty and not to banishment.</div>
	  <div class="direction">Exeunt</div>
	  </div>
	</div>
	</div>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    unittest.main()
