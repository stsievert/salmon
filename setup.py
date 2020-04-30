#!/usr/bin/env python

from distutils.core import setup
import versioneer

version = "v0.1"
setup(
    name="Salmon",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Efficient crowdsourcing of triplet queries",
    author="Scott Sievert",
    author_email="dev@stsievert.com",
    url="https://stsievert.com/salmon",
    packages=["salmon"],
)
