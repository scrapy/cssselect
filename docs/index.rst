.. module:: cssselect

.. include:: ../README.rst


.. contents:: Contents
    :local:
    :depth: 1

Quickstart
==========

Use :class:`HTMLTranslator` for HTML documents, :class:`GenericTranslator`
for "generic" XML documents. (The former has a more useful translation
for some selectors, based on HTML-specific element types or attributes.)


.. sourcecode:: pycon

    >>> from cssselect import GenericTranslator, SelectorError
    >>> try:
    ...     expression = GenericTranslator().css_to_xpath('div.content')
    ... except SelectorError:
    ...     print('Invalid selector.')
    ...
    >>> print(expression)
    descendant-or-self::div[@class and contains(concat(' ', normalize-space(@class), ' '), ' content ')]

The resulting expression can be used with lxml's `XPath engine`_:

.. _XPath engine: http://lxml.de/xpathxslt.html#xpath

.. sourcecode:: pycon

    >>> from lxml.etree import fromstring
    >>> document = fromstring('''
    ...   <div id="outer">
    ...     <div id="inner" class="content body">text</div>
    ...   </div>
    ... ''')
    >>> [e.get('id') for e in document.xpath(expression)]
    ['inner']

User API
========

In CSS3 Selectors terms, the top-level object is a `group of selectors`_, a
sequence of comma-separated selectors. For example, ``div, h1.title + p``
is a group of two selectors.

.. _group of selectors: http://www.w3.org/TR/selectors/#grouping

.. autofunction:: parse
.. autoclass:: Selector()
    :members:

.. autoclass:: FunctionalPseudoElement

.. autoclass:: GenericTranslator
    :members: css_to_xpath, selector_to_xpath

.. autoclass:: HTMLTranslator

Exceptions
----------

.. autoexception:: SelectorError
.. autoexception:: SelectorSyntaxError
.. autoexception:: ExpressionError


Supported selectors
===================

This library implements CSS3 selectors as described in `the W3C specification
<http://www.w3.org/TR/2011/REC-css3-selectors-20110929/>`_, plus a few parts
of Level 4. The table below lists every selector *cssselect* recognizes and
whether it can be translated to XPath 1.0; selectors it does not recognize at
all raise :class:`SelectorSyntaxError`, and recognized-but-untranslatable ones
raise :class:`ExpressionError`.

.. list-table::
    :header-rows: 1
    :widths: auto

    * - Selector
      - Support
    * - ``*``, ``e``, ``ns|e``, ``*|e``, ``|e``
      - Yes
    * - ``e#id``, ``e.class``
      - Yes
    * - ``[attr]``, ``[attr=val]``, ``[attr~=val]``, ``[attr|=val]``,
        ``[attr^=val]``, ``[attr$=val]``, ``[attr*=val]``,
        ``[namespace|attr...]``
      - Yes
    * - ``e f``, ``e > f``, ``e + f``, ``e ~ f``
      - Yes
    * - ``e, f`` (grouping)
      - Yes
    * - ``:first-child``, ``:last-child``, ``:only-child``
      - Yes
    * - ``e:first-of-type``, ``e:last-of-type``, ``e:only-of-type``,
        ``e:nth-of-type()``, ``e:nth-last-of-type()``
      - Yes, when an element type is given
    * - ``*:first-of-type``, ``*:last-of-type``, ``*:only-of-type``,
        ``*:nth-of-type()``, ``*:nth-last-of-type()``
      - No: counting same-type siblings needs a concrete type, and ``*``
        does not have one
    * - ``:nth-child()``, ``:nth-last-child()``
      - Yes, including the ``even``, ``odd`` and ``an+b`` forms
    * - ``:empty``, ``:root``
      - Yes
    * - ``:lang()``
      - Yes
    * - ``:not(compound or complex selector)``
      - Yes, for a single argument; ``:not(a, b)`` (a selector list) is not
        supported
    * - ``:hover``, ``:active``, ``:focus``, ``:target``, ``:visited``
      - Parsed, but never matches: there is no interactivity or link
        history to base this on
    * - ``:link``, ``:enabled``, ``:disabled``, ``:checked``
      - Never matches in :class:`GenericTranslator`; matched based on
        HTML-specific elements and attributes in :class:`HTMLTranslator`
    * - ``::before``, ``::after``, ``::first-line``, ``::first-letter``,
        ``::marker``, functional pseudo-elements
      - Parsed into :attr:`Selector.pseudo_element`, but rejected by
        :meth:`~GenericTranslator.css_to_xpath`: XPath has no notion of a
        pseudo-element, so it is up to the caller to handle these
    * - ``:scope``
      - Yes, only at the start of a selector (Level 4)
    * - ``:is()``, ``:where()``, and their alias ``:matches()``
      - Yes, for a comma-separated list of *compound* selectors; a
        combinator (``:is(a b)``), ``:not()`` or ``:scope`` inside the
        arguments is not supported, but ``:has()`` is (Level 4)
    * - ``:has()``
      - Yes, for a single argument made of an optional leading combinator
        (``>``, ``+`` or ``~``) followed by one *compound selector* built
        only from type, class and universal selectors, e.g.
        ``:has(> a.important)``; anything else, such as an ID
        (``:has(#id)``) or a selector list (``:has(a, b)``), is not
        supported (Level 4)
    * - Case-insensitive (``i``) and case-sensitive (``s``) attribute value
        flags, ``:nth-child(An+B of S)``, ``:dir()``, ``:focus-within``,
        ``:focus-visible``, ``:default``, ``:placeholder-shown``,
        ``:read-only``/``:read-write``, ``:required``/``:optional``,
        ``:valid``/``:invalid``/``:in-range``/``:out-of-range``,
        ``:current``/``:past``/``:future``,
        ``:nth-col()``/``:nth-last-col()``, ``:host()``/``:host-context()``,
        ``::selection``, ``::placeholder``, ``::part()``, ``::slotted()``
      - Not implemented; several of these need document or runtime state
        cssselect has no access to, or a shadow DOM concept that has no
        XPath equivalent

This is not an exhaustive list of every Level 4 (or later) selector; a
selector that is not mentioned here at all is not implemented either.

These are non-standard extensions:

* ID selectors whose value is not a valid CSS identifier, e.g. ``#37signals``.
  The specification only allows an identifier after ``#``, so such IDs, which
  are valid in HTML, would otherwise require ``[id="37signals"]``.
* The ``:contains(text)`` pseudo-class that existed in `an early draft`_
  but was then removed.
* The ``!=`` attribute operator. ``[foo!=bar]`` is the same as
  ``:not([foo=bar])``, except for an empty value: ``[foo!='']`` matches only
  elements that do have a ``foo`` attribute and whose value is not empty,
  while ``:not([foo=''])`` also matches elements without a ``foo`` attribute.

.. _an early draft: http://www.w3.org/TR/2001/CR-css3-selectors-20011113/#content-selectors

..
    The following claim was copied from lxml:

    """
    XPath has underspecified string quoting rules (there seems to be no
    string quoting at all), so if you use expressions that contain
    characters that requiring quoting you might have problems with the
    translation from CSS to XPath.
    """

    It seems "string quoting" meant "quote escaping". There is indeed
    no quote escaping, but the xpath_literal method handles this.
    It should not be a problem anymore.


Examples
========

Every example below runs as a doctest alongside the test suite, so it stays
correct as the translation logic changes.

.. sourcecode:: pycon

    >>> from cssselect import GenericTranslator
    >>> def xpath(css, translator=GenericTranslator()):
    ...     return translator.css_to_xpath(css, prefix="")

Type, universal, namespace, ID and class selectors:

.. sourcecode:: pycon

    >>> xpath("*")
    '*'
    >>> xpath("e")
    'e'
    >>> xpath("ns|e")
    'ns:e'
    >>> xpath("e#myid")
    "e[@id = 'myid']"
    >>> xpath("e.warning")
    "e[@class and contains(concat(' ', normalize-space(@class), ' '), ' warning ')]"

Attribute selectors:

.. sourcecode:: pycon

    >>> xpath("e[foo]")
    'e[@foo]'
    >>> xpath('e[foo="bar"]')
    "e[@foo = 'bar']"
    >>> xpath('e[foo~="bar"]')
    "e[@foo and contains(concat(' ', normalize-space(@foo), ' '), ' bar ')]"
    >>> xpath('e[foo^="bar"]')
    "e[@foo and starts-with(@foo, 'bar')]"
    >>> xpath('e[foo$="bar"]')
    "e[@foo and substring(@foo, string-length(@foo)-2) = 'bar']"
    >>> xpath('e[foo*="bar"]')
    "e[@foo and contains(@foo, 'bar')]"
    >>> xpath('e[foo|="en"]')
    "e[@foo and (@foo = 'en' or starts-with(@foo, 'en-'))]"
    >>> xpath("e[foo!=bar]")  # non-standard extension
    "e[not(@foo) or @foo != 'bar']"

Combinators and grouping:

.. sourcecode:: pycon

    >>> xpath("e f")
    'e/descendant-or-self::*/f'
    >>> xpath("e > f")
    'e/f'
    >>> xpath("e + f")
    'e/following-sibling::*[(self::f) and (position() = 1)]'
    >>> xpath("e ~ f")
    'e/following-sibling::f'
    >>> xpath("e, f")
    'e | f'

Structural pseudo-classes:

.. sourcecode:: pycon

    >>> xpath("e:first-child")
    'e[count(preceding-sibling::*) = 0]'
    >>> xpath("e:nth-child(3n+2)")
    'e[(count(preceding-sibling::*) >= 1) and ((count(preceding-sibling::*) +2) mod 3 = 0)]'
    >>> xpath("e:only-child")
    'e[count(preceding-sibling::*) = 0 and count(following-sibling::*) = 0]'
    >>> xpath("e:empty")
    'e[not(*) and not(string-length())]'
    >>> xpath("e:root")
    'e[not(parent::*)]'

``:not()``, ``:is()``, ``:where()`` and ``:has()``:

.. sourcecode:: pycon

    >>> xpath("e:not(a > b)")
    'e[not(self::b and parent::*[self::a])]'
    >>> xpath("e:where(foo, bar)")
    'e[(self::foo) or (self::bar)]'
    >>> xpath("e:has(> f)")
    'e[./f]'
    >>> xpath("div:has(bar.foo)")
    "div[descendant::bar[@class and contains(concat(' ', normalize-space(@class), ' '), ' foo ')]]"

``:lang()`` and the non-standard ``:contains()``:

.. sourcecode:: pycon

    >>> xpath("e:lang(en)")
    "e[lang('en')]"
    >>> xpath('e:contains("foo")')
    "e[contains(., 'foo')]"


How selectors become XPath
===========================

Translating a selector is two independent steps, one per module.

Parsing
-------

In :file:`cssselect/parser.py`, :func:`parse` tokenizes the CSS source
(``tokenize()``) and feeds the resulting ``Token`` stream to a small
recursive-descent parser: ``parse_selector_group()`` splits a
comma-separated group, ``parse_selector()`` handles combinators, and
``parse_simple_selector()`` handles everything that can appear in a single
compound selector (type, ``#id``, ``.class``, ``[attr]``, and
pseudo-classes/elements). Each construct becomes one node of a *parsed
tree*, wrapped in a :class:`Selector`:

.. list-table::
    :header-rows: 1

    * - CSS
      - Parsed as
    * - ``e``, ``*``, ``ns|e``
      - ``Element``
    * - ``#id``
      - ``Hash``
    * - ``.class``
      - ``Class``
    * - ``[attr...]``
      - ``Attrib``
    * - ``:name`` (no arguments)
      - ``Pseudo``
    * - ``:name(...)`` (other than the ones below)
      - ``Function``
    * - ``:not(...)``
      - ``Negation``
    * - ``:has(...)``
      - ``Relation``
    * - ``:is(...)``, ``:matches(...)``
      - ``Matching``
    * - ``:where(...)``
      - ``SpecificityAdjustment``
    * - ``e f``, ``e > f``, ``e + f``, ``e ~ f``
      - ``CombinedSelector``

Translation
-----------

In :file:`cssselect/xpath.py`, ``GenericTranslator.xpath()`` walks that tree
and turns it into an ``XPathExpr``, a small builder that accumulates an
XPath ``path`` (e.g. ``foo/descendant-or-self::*/``), an ``element`` node
test, and a predicate ``condition``, joined together into a string. It
dispatches on the parsed node's class name, lower-cased and prefixed with
``xpath_``, e.g. an ``Attrib`` node is handled by ``xpath_attrib()``.

A handful of node types dispatch a second time, by name, to keep one method
per CSS construct instead of one large method with a chain of ``if``\\ s.
The method name is always ``xpath_`` + that name (``-`` becomes ``_``) +
a suffix identifying the kind of dispatch:

* ``Pseudo`` (``:name``) and ``Function`` (``:name(...)``) dispatch on the
  pseudo-class or function name, e.g. ``:first-child`` and ``:nth-child()``
  are handled by ``xpath_first_child_pseudo()`` and
  ``xpath_nth_child_function()``. These two are open-ended: adding a
  pseudo-class or function is adding a method with the matching name.
* ``CombinedSelector`` and ``Relation`` (whose subselector can carry its own
  leading combinator, e.g. ``:has(> a)``) dispatch on the combinator, mapped
  by name in ``GenericTranslator.combinator_mapping``, e.g. ``>`` becomes
  ``xpath_child_combinator()`` and ``xpath_relation_child_combinator()``
  respectively.
* ``Attrib`` dispatches on the attribute operator, mapped by name in
  ``GenericTranslator.attribute_operator_mapping``, e.g. ``^=`` becomes
  ``xpath_attrib_prefixmatch()``.

``xpath_negation()`` (``:not()``), ``xpath_matching()``
(``:is()``/``:matches()``) and ``xpath_specificityadjustment()``
(``:where()``) are the exceptions: their CSS name does not appear in the
Python method name, since none of them dispatch further by name.

``:not()`` is also the one construct not translated by walking left to
right: matching e.g. ``a:not(b > c)`` means testing, on the context node
itself, whether it is a ``c`` whose parent is a ``b`` — the reverse of how
``b > c`` alone would be read. ``_xpath_match_condition()`` does this by
walking the ``:not()`` argument right to left, turning each combinator into
the matching reverse axis from
``GenericTranslator._reverse_combinator_mapping`` (e.g. ``>`` becomes
``parent::*``).

:class:`HTMLTranslator` overrides a handful of these hooks (``:link``,
``:checked``, ``:enabled``, ``:disabled`` and ``:lang()``) with
HTML-specific logic, and three case-folding flags, but otherwise reuses
everything above.


Customizing the translation
===========================

Just like :class:`HTMLTranslator` is a subclass of :class:`GenericTranslator`,
you can make new sub-classes of either of them and override some methods.
This enables you, for example, to customize how some pseudo-class is
implemented without forking or monkey-patching cssselect.

The "customization API" is the set of methods in translation classes
and their signature. You can look at the `source code`_ to see how it works.
However, be aware that this API is not very stable yet. It might change
and break your sub-class.

.. _source code: https://github.com/scrapy/cssselect/blob/master/cssselect/xpath.py


Namespaces
==========

In CSS you can use ``namespace-prefix|element``, similar to
``namespace-prefix:element`` in an XPath expression.  In fact, it maps
one-to-one. How prefixes are mapped to namespace URIs depends on the
XPath implementation.

.. include:: ../CHANGES
