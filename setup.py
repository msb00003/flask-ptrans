#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='flask-ptrans',
    version='0.5',
    description='Flask extension for localisation of templates from JSON files',
    author='Peter Harris',
    author_email='peter.harris@skyscanner.net',
    url='https://github.com/Skyscanner/flask-ptrans',
    packages=find_packages(),
    install_requires=['flask'],
    extras_require={'test': 'nose'},
    entry_points={
        'console_scripts': [
            'aggregate_json = flask_ptrans.scripts.aggregate_json:main',
            'resolve_json_conflicts = flask_ptrans.scripts.resolve_json_conflicts:main',
            'check_templates = flask_ptrans.scripts.check_templates:main',
            'list_untranslated_strings = flask_ptrans.scripts.list_untranslated_strings:main',
            'pseudolocalise = flask_ptrans.scripts.pseudolocalise:main',
        ]
        },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        ],
    license='Apache License v2',
    )
