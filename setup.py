#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import find_packages
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    with open(file_path, encoding="utf-8") as file_handle:
        return file_handle.read()


requirements = ["pytest>=4.0.0"]

setup(
    name="pytest-subprocess",
    version="1.5.0",
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
    python_requires=">=3.6",
    install_requires=requirements,
    extras_require={
        "test": [
            "pytest>=4.0",
            "coverage",
            "docutils>=0.12",
            "Pygments>=2.0",
            "pytest-rerunfailures",
            "pytest-asyncio>=0.15.1",
            "anyio",
        ],
        "dev": ["nox", "changelogd"],
        "docs": [
            "sphinx",
            "furo",
            "sphinxcontrib-napoleon",
            "sphinx-autodoc-typehints",
            "changelogd",
        ],
    },
    packages=find_packages(exclude=["docs", "tests"]),
    package_data={"pytest_subprocess": ["py.typed"]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "pytest11": [
            "subprocess = pytest_subprocess.fixtures",
        ],
    },
)
