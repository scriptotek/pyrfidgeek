import logging
from .rfidgeek import PyRFIDGeek, ISO14443A, ISO14443B, ISO15693
from .crc import CRC

# Logging: Add a null handler to avoid "No handler found" warnings.
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
