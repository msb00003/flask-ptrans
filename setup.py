#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='flask-ptrans',
    version='1.5',
    description='Flask extension for localisation of templates from JSON files',
    author='Peter Harris',
    author_email='peter.harris@skyscanner.net',
    url='https://github.com/Skyscanner/flask-ptrans',
    download_url='https://github.com/Skyscanner/flask-ptrans/tarball/1.5',
    packages=find_packages(),
    install_requires=[],
    extras_require={'test': 'nose', 'flask': 'flask'},
    entry_points={
        'console_scripts': [
            'ptrans_aggregate = flask_ptrans.scripts.aggregate_json:main',
            'ptrans_resolve = flask_ptrans.scripts.resolve_json_conflicts:main',
            'ptrans_check = flask_ptrans.scripts.check_templates:main',
            'ptrans_untranslated = flask_ptrans.scripts.list_untranslated_strings:main',
            'ptrans_pseudolocalise = flask_ptrans.scripts.pseudolocalise:main',
        ]
        },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Flask',
        'Framework :: Tornado',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        ],
    keywords=['localisation', 'jinja2', 'flask', 'pootle', 'tornado'],
    license='Apache License v2',
    )
