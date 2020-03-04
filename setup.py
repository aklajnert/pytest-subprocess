#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from setuptools import find_packages
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with open(file_path, encoding="utf-8") as file_handle:
        return file_handle.read()


requirements = ["pytest>=4.0.0"]
if sys.version_info <= (3, 5):
    requirements.append("typing")

setup(
    name="pytest-subprocess",
    version="0.1.3",
    author="Andrzej Klajnert",
    author_email="python@aklajnert.pl",
    maintainer="Andrzej Klajnert",
    maintainer_email="python@aklajnert.pl",
    license="MIT",
    project_urls={
        "Documentation": "https://pytest-subprocess.readthedocs.io",
        "Source": "https://github.com/aklajnert/pytest-subprocess",
        "Tracker": "https://github.com/aklajnert/pytest-subprocess/issues",
    },
    description="A plugin to fake subprocess for pytest",
    long_description=read("README.rst") + "\n" + read("HISTORY.rst"),
    py_modules=["pytest_subprocess"],
    python_requires=">=3.4",
    install_requires=requirements,
    extras_require={
        "test": [
            "pytest>=4.0",
            "coverage",
            "docutils>=0.12",
            "Pygments>=2.0",
            "pytest-azurepipelines",
        ],
        "dev": ["nox", "changelogd"],
        "docs": [
            "sphinx",
            "sphinxcontrib-napoleon",
            "sphinx-autodoc-typehints",
            "changelogd",
        ],
    },
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
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={"pytest11": ["subprocess = pytest_subprocess.fixtures",],},
)
