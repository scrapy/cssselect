.. module:: cssselect
.. include:: ../README.rst

User API
========

The ``cssselect`` module provides two classes:

* :class:`GenericTranslator` for "generic" XML documents.
* :class:`HTMLTranslator` for HTML documents.

Both are instanciated without arguments.
Currently, their only public API is the :meth:`~GenericTranslator.css_to_xpath`
method. This API
expected to expand to provide more information about the parsed selectors,
and to allow customization of the translation.


.. automethod:: GenericTranslator.css_to_xpath


Limitations and supported selectors
===================================

This library implements CSS3 selectors as described in `the W3C specification
<http://www.w3.org/TR/2011/REC-css3-selectors-20110929/>`_.
In this context however, there is no interactivity or history of visited links.
Therefore, these pseudo-classes are accepted but never match anything:

* ``:hover``
* ``:active``
* ``:focus``
* ``:target``
* ``:visited``

Additionally, these depend on document knowledge and only have a useful
implementation in :class:`HTMLTranslator`. In :class:`GenericTranslator`,
they never match:

* ``:link``
* ``:enabled``
* ``:disabled``
* ``:checked``

These applicable pseudo-classes are not yet implemented:

* ``:lang(language)``
* ``*:first-of-type``, ``*:last-of-type``, ``*:nth-of-type``,
  ``*:nth-last-of-type``, ``*:only-of-type``.  All of these work when
  you specify an element type, but not with ``*``

None of the pseudo-elements apply since XPath only knows about “real”
elements.

..
    The following claim was copied from lxml.
    TODO: is this true? What kind of situation could cause trouble?
    Maybe add an example?

XPath has underspecified string quoting rules (there seems to be no
string quoting at all), so if you use expressions that contain
characters that requiring quoting you might have problems with the
translation from CSS to XPath.

On the other hand, *cssselect* supports some selectors that are not
in the Level 3 specification:

* The ``:contains(text)`` pseudo-class that `existed in an early draft
  <http://www.w3.org/TR/2001/CR-css3-selectors-20011113/#content-selectors>`_
  but was then removed.
* The ``!=`` attribute operator. ``[foo!=bar]`` is the same as
  ``:not([foo=bar])``


Customizing the translation
===========================

Just like :class:`HTMLTranslator` is a subclass of :class:`GenericTranslator`,
you can make new sub-classes of either of them and override some methods.
This way, you can customize how eg. some pseudo-class is implemented or change
some other detail of the XPath translation, without forking or monkey-patching
cssselect.

The "customization API" is the set of methods in translation classes
and their signature. You can look at the source code to see how it works.
However, be aware that this API is not very stable yet. It might change
and break you sub-class.


Namespaces
==========

In CSS you can use ``namespace-prefix|element``, similar to
``namespace-prefix:element`` in an XPath expression.  In fact, it maps
one-to-one. How prefixes are mapped to namespace URIs depends on the
XPath implementation.

.. include:: ../CHANGES
