#!/usr/bin/env python

from distutils.core import setup
from os.path import exists
from glob import glob

import versioneer

#  breakpoint()
with open("./requirements.txt", "r") as f:
    install_requires = [r for r in f.read().split("\n") if r]

packages = [
    "salmon",
    "salmon.frontend",
    "salmon.backend",
    "salmon.triplets",
    "salmon._out",
]

long_description = """Salmon is a tool for efficiently generating ordinal
embeddings. It relies on "active" machine learning algorithms to choose the
most informative queries for humans to answer."""

setup(
    name="salmon-triplets",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Efficient crowdsourcing for ordinal embeddings",
    author="Scott Sievert",
    author_email="salmon@stsievert.com",
    url="https://docs.stsievert.com/salmon",
    packages=packages,
    install_requires=install_requires,
    tests_require=["pytest"],
    python_requires=">=3.8.*",
    long_description=long_description,
    data_files=[("requirements", ["requirements.txt"])],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
    ],
)
