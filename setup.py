#!/usr/bin/env python
# -*- coding: utf-8 -*-
import codecs
import os

from setuptools import find_packages
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-subprocess",
    version="0.1.1",
    author="Andrzej Klajnert",
    author_email="python@aklajnert.pl",
    maintainer="Andrzej Klajnert",
    maintainer_email="python@aklajnert.pl",
    license="MIT",
    url="https://github.com/aklajnert/pytest-subprocess",
    description="A plugin to fake subprocess for pytest",
    long_description=read("README.rst"),
    py_modules=["pytest_subprocess"],
    python_requires=">=3.4",
    install_requires=["pytest>=4.0.0"],
    packages=find_packages(exclude=["docs", "tests"]),
    package_data={"pytest_subprocess": ["py.typed", "core.pyi", "fixtures.pyi",]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["subprocess = pytest_subprocess.fixtures",],},
)
