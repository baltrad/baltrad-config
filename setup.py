#!/usr/bin/env python
import setuptools
import sys

REQUIRED_PACKAGES= [
    "pyasn1",
    "pycrypto >= 2.4",
    "python-keyczar >= 0.7b",
]
if sys.version_info > (3,):
    REQUIRED_PACKAGES= [
    "pyasn1",
    "pycrypto >= 2.4",
    "python3-keyczar >= 0.71rc0",
]

setuptools.setup(name="baltrad.config",
    version="0.1-dev",
    namespace_packages=["baltrad"],
    zip_safe=False,
    packages=setuptools.find_packages(
        "src",
        exclude=["*.tests.*", "*.tests"],
    ),
    package_dir={
        "": "src"
    },
    install_requires=REQUIRED_PACKAGES,
    entry_points = {
        "console_scripts" : [
            "baltrad-config = baltrad.config.main:run",
        ]
    },
)
