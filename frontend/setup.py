#!/usr/bin/env python

from distutils.core import setup
import versioneer

setup(
    name="salmon-frontend",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Frontend for Salmon",
    author="Scott Sievert",
    author_email="dev@stsievert.com",
    url="https://github.com/stsievert/salmon",
    packages=["frontend"],
)
