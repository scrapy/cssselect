import os.path
from setuptools import setup


README = open(os.path.join(os.path.dirname(__file__), 'README')).read()


setup(
    name='cssselect',
    version='0.1',
    author='Ian Bicking',
    author_email='ianb@colorstudy.com',
    maintainer='Simon Sapin',
    maintainer_email='simon.sapin@exyr.org',
    description='cssselect is a parser for CSS Selectors that can translate '
                'to XPath 1.0',
    long_description=README,
    url='http://packages.python.org/cssselect/',
    license='BSD',
    install_requires='lxml',
    py_modules = ['cssselect', 'test_cssselect'],  # XXX include the tests?
    test_suite='test_cssselect',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
    ],
)
