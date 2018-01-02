import logging
from .rfidgeek import PyRFIDGeek, ISO14443A, ISO14443B, ISO15693
from .crc import CRC

import pkg_resources  # part of setuptools
__version__ = pkg_resources.require('rfidgeek')[0].version

# Logging: Add a null handler to avoid "No handler found" warnings.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
