#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

from distutils.core import setup

setup(name='PyRFIDGeek',
      version='2.0',
      description='Serial communication with RFIDGeek boards',
      author='Dan Michael O. Heggø',
      author_email='d.m.heggo@ub.uio.no',
      packages=['rfidgeek'],
      requires=['pyserial'],
      zip_safe=True
     )
