from setuptools import setup

setup(
    name='cssselect',
    version='0.1dev',
    url='http://packages.python.org/cssselect/',
    license='BSD',
    install_requires='lxml',
    py_modules = ['cssselect', 'test_cssselect'],  # XXX include the tests?
    test_suite='test_cssselect',
)
