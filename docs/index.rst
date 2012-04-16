.. include:: ../README.rst

User API
========

.. module:: cssselect

Currently, the only public API is the ``css_to_xpath()`` function. This API
expected to expand to provide more information about the parsed selectors,
and to allow customization of the translation.

.. autofunction:: css_to_xpath(css, prefix='descendant-or-self::')


Namespaces
==========

In CSS you can use ``namespace-prefix|element``, similar to
``namespace-prefix:element`` in an XPath expression.  In fact, it maps
one-to-one. How prefixes are mapped to namespace URIs depends on the
XPath implementation.


Limitations and supported selectors
===================================

This library attempts to implement CSS3 selectors as described in
`the W3C specification
<http://www.w3.org/TR/2011/REC-css3-selectors-20110929/>`_. Some of
the pseudo-classes do not apply in this context.
In particular these will not be available:

* link state: ``:link``, ``:visited``, ``:target``
* actions: ``:hover``, ``:active``, ``:focus``
* UI states: ``:enabled``, ``:disabled`` (``:checked`` *is* available)

Also, none of the pseudo-elements apply since XPath only knows about “real”
elements.


These applicable pseudoclasses are not yet implemented:

* ``:lang(language)``
* ``*:first-of-type``, ``*:last-of-type``, ``*:nth-of-type``,
  ``*:nth-last-of-type``, ``*:only-of-type``.  All of these work when
  you specify an element type, but not with ``*``

XPath has underspecified string quoting rules (there seems to be no
string quoting at all), so if you use expressions that contain
characters that requiring quoting you might have problems with the
translation from CSS to XPath.

.. include:: ../CHANGES
