#!/usr/bin/env python
import setuptools
import sys

REQUIRED_PACKAGES= [
    "baltrad-crypto",
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
    package_data={'': ['server.xml.template']},
    include_package_data=True,
    install_requires=REQUIRED_PACKAGES,
    entry_points = {
        "console_scripts" : [
            "baltrad-config = baltrad.config.main:run",
            "bltcfg = baltrad.config.bltcmd:run",
            "bltgroovyroute = baltrad.config.bltgroovyroute:run"
        ]
    },
)
