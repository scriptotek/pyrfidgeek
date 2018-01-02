#!/usr/bin/python
import logging
import thread
import time
import json
import yaml
import time
from copy import copy

from rfidgeek import PyRFIDGeek, ISO15693

# You might need to change this:
COM_PORT_NAME = '/dev/tty.SLAB_USBtoUART'

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

rfid = PyRFIDGeek(serial_port=COM_PORT_NAME, debug=True)
rfid.set_protocol(ISO15693)
uids = list(rfid.inventory())
if len(uids) == 1:
    rfid.enable_led(5)
    tag = rfid.erase_card(uids[0])
    rfid.disable_led(5)
else:
    logger.error('Found %d tags, not 1' % (len(uids)))
