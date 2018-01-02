#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

from setuptools import setup

setup(
    name='rfidgeek',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='2.0.0',

    description='Read/write ISO 15693 cards following the Danish RFID data model for libraries',
    long_description='Read/write ISO 15693 cards following the Danish RFID data model for libraries, using serial communication to [RFIDGeek](http://rfidgeek.com/) boards.',
    url='https://github.com/scriptotek/pyrfidgeek',
    author='Dan Michael O. Heggø',
    author_email='d.m.heggo@ub.uio.no',
    license='MIT',
    keywords='rfid iso15693 iso14443 libdev',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    packages=['rfidgeek'],

    # Run-time dependencies
    install_requires=['pyserial'],

    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-pep8']
)
