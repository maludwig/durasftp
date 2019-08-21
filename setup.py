#!/usr/bin/env python
"""Setup script for realpython-reader"""

import os.path
from setuptools import setup, find_packages

# The directory containing this file
HERE = os.path.abspath(os.path.dirname(__file__))

# The text of the README file
with open(os.path.join(HERE, "README.md")) as fid:
    README = fid.read()

# This call to setup() does all the work
setup(
    name="durasftp",
    version="1.0.0",
    description="Durable SFTP connections",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/maludwig/durasftp",
    author="maludwig",
    author_email="mitchell.ludwig@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    # packages=['durasftp'],
    packages=find_packages(exclude=["*.test", "*.test.*", "test.*", "test"]),
    include_package_data=False,
    install_requires=[
        "pysftp>=0.2.9", "arrow>=0.14.4"
    ],
    python_requires='>=3.5',
    entry_points={"console_scripts": ["realpython=reader.__main__:main"]},
)
