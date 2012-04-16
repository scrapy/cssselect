"""
    CSS Selectors based on XPath
    ============================

    This module supports selecting XML/HTML elements based on CSS selectors.
    See the `CSSSelector` class for details.


    :copyright: (c) 2007-2012 Ian Bicking and contributors.
                See AUTHORS for more details.
    :license: BSD, see LICENSE for more details.

"""

from cssselect.parser import SelectorError
from cssselect.xpath import Translator


VERSION = '0.2'
__version__ = VERSION

css_to_xpath = Translator().css_to_xpath
