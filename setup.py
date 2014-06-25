#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='cloudfoundry',
    version='0.1.0',
    description='Generate CF charms from metadata',
    long_description=readme + '\n\n' + history,
    author='Benjamin Saller',
    author_email='benjamin.saller@canonical.com',
    url='https://github.com/bcsaller/charmgen',
    packages=[
        'charmgen',
        'cloudfoundry'
    ],
    package_dir={'charmgen': 'charmgen',
                 'cloudfoundry': 'cloudfoundry'},
    license="BSD",
    zip_safe=False,
    keywords='cloudfoundry',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    entry_points={
        'console_scripts': [
            'generate_charm = charmgen.generator:main',
            'get_relations = charmgen.getrels:main',
            'diff_revisions = charmgen.differ:main'

        ]
    }
)
