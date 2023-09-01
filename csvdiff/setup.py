# SPDX-FileCopyrightText: 2023 Technology Innovation Institute (TII)
#
# SPDX-License-Identifier: Apache-2.0

# pylint: disable=invalid-name, import-error, missing-function-docstring

""" setup.py for setuptools """

import os.path
import setuptools

with open("README.md", encoding="utf-8") as readme:
    long_description = readme.read()


def project_path(*names):
    return os.path.join(os.path.dirname(__file__), *names)


with open(project_path("VERSION"), encoding="utf-8") as f:
    version = f.read().strip()

requires = [
    "pandas",
    "colorlog",
    "wheel",
]

setuptools.setup(
    name="csvdiff",
    version=version,
    description="Utility that compares two csv files",
    author="TII",
    author_email="henri.rosten@unikie.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    install_requires=requires,
    license="Apache-2.0",
    classifiers=[  # See:https://pypi.org/classifiers/
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
    ],
    packages=["csvdiff"],
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "csvdiff = csvdiff.main:main",
        ]
    },
)
