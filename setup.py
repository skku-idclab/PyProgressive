# generate setup.py for this package
#
from setuptools import setup, find_packages

setup(
    name='progressive',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'sympy'
    ]
)
