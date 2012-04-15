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
from cssselect.parser import SelectorSyntaxError, ExpressionError
from cssselect.xpath import Translator

__all__ = ['SelectorSyntaxError', 'ExpressionError', 'css_to_xpath']


def css_to_xpath(css, prefix='descendant-or-self::', translator=None):
    if translator is None:
        translator = Translator()
    return translator.css_to_xpath(css, prefix=prefix)
