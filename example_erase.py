#!/usr/bin/python
import logging
import thread
import time
import json
import argparse
import yaml
import time
from copy import copy

from pyrfidgeek import PyRFIDGeek, ISO15693

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek write patron card example')
parser.add_argument('--config', nargs='?', default='config.yml', help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

rfid = PyRFIDGeek(config)
rfid.set_protocol(ISO15693)
uids = list(rfid.inventory())
if len(uids) == 1:
	rfid.enable_led(5)
	tag = rfid.erase_card(uids[0])
	rfid.disable_led(5)
else:
	logger.error('Found %d tags, not 1' % (len(uids)))
