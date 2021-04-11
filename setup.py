#!/usr/bin/env python

from distutils.core import setup
import versioneer

#  with open("requirements.txt") as f:
#  requirements = f.read().splitlines()

setup(
    name="salmon",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Efficient crowdsourcing of triplet queries",
    author="Scott Sievert",
    author_email="dev@stsievert.com",
    url="https://docs.stsievert.com/salmon",
    packages=["salmon"],
    #  install_requires=requirements,
)
