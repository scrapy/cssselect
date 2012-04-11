from setuptools import setup, find_packages

setup(
    name='cssselect',
    version='0.1dev',
    url='http://packages.python.org/cssselect/',
    license='BSD',
    packages=find_packages(),
    package_data={'cssselect.tests': ['*.html']},
)
