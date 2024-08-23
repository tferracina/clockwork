"""Set up for the clockwork package."""


#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='clockwork',
    version='1.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'tabulate',
        'matplotlib',
    ],
    entry_points={
        'console_scripts': [
            'clockwork=clockwork:clockwork',
        ],
    },
)
