# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

import logging
import argparse
import yaml
#import pyreadline
import sys
import serial
import time
from termcolor import colored

from pyrfidgeek import PyRFIDGeek


# def rlinput(prompt, prefill=''):
#     readline.set_startup_hook(lambda: readline.insert_text(prefill))
#     try:
#         return raw_input(prompt)
#     finally:
#         readline.set_startup_hook()


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek writer example')
parser.add_argument('--config', nargs='?', default='config.yml',
                    help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

try:
    reader = PyRFIDGeek(config)
except serial.serialutil.SerialException:
    print "Failed to open serialport " + config['serial']['port']
    sys.exit(1)


try:

    uids = []
    while len(uids) == 0:
        uids = list(reader.inventory())
        print 
        print 'Found %d tag(s)' % len(uids)

        # Check if all tags are blank:
        for uid in uids:
            item = reader.read_danish_model_tag(uid)
            if item['id'] != '':
                print ' # Warning: Found a non-blank tag.'
                print
                #answer = rlinput(colored('Overwrite tag? ', 'red'), 'n').lower()
                answer = input('Overwrite tag? [y/n]').lower()
                if answer != 'y' and answer != 'j':
                    sys.exit(0)

        for partno, uid in enumerate(uids, start=1):
            dokid = input('Enter dokid: ')
            data = {
                'id': dokid,
                'partno': partno,
                'nparts': len(uids),
                'country': 'NO',
                'library': '1032204'
                }
            if reader.write_danish_model_tag(uid, data):
                print 'ok'
            else:
                print 'oh noes, write failed'

        time.sleep(1)

finally:
    reader.close()
