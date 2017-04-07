# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0
from __future__ import print_function
import logging
import argparse
import yaml
#import pyreadline
import sys
import serial
import time
from termcolor import colored

from rfidgeek import PyRFIDGeek, ISO15693

# You might need to change this:
COM_PORT_NAME='/dev/tty.SLAB_USBtoUART'

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


try:
    reader = PyRFIDGeek(serial_port=COM_PORT_NAME, debug=True)
except serial.serialutil.SerialException:
    print("Failed to open serial port " + config['serial']['port'])
    sys.exit(1)

reader.set_protocol(ISO15693)


try:

    uids = []
    while len(uids) == 0:
        uids = list(reader.inventory())
        print()
        if len(uids) == 0:
            print()
            print('Please add a new book')
            print()
        else:
            print('Found %d tag(s)' % len(uids))

        # Check if all tags are blank:
        for uid in uids:
            item = reader.read_danish_model_tag(uid)
            print(item)
            if not 'id' in item:
                print(item)
            elif item['id'] != '':
                print()
                print(' ##########################################')
                print(' # Warning: Found a non-blank tag         #')
                print(' ##########################################')
                print()
                #answer = rlinput(colored('Overwrite tag? ', 'red'), 'n').lower()
                answer = raw_input('Overwrite tag? [y/n]').lower()
                if answer != 'y' and answer != 'j':
                    sys.exit(0)

        data = {
            'nparts': len(uids),
            'country': 'NO',
            'library': '1030310'
            }

        if len(uids) != 0:
            print
            print('Libnr: %(library)s, Country: %(country)s, Parts: %(nparts)s' % data)
            data['id'] = raw_input('Enter/scan document ID: ')

            for partno, uid in enumerate(uids, start=1):
                data['partno'] = partno
                if reader.write_danish_model_tag(uid, data):
                    print('ok')
                else:
                    print()
                    print(' ##########################################')
                    print(' # Oh noes, write failed!                 #')
                    print(' ##########################################')
                    print()
                    sys.exit(0)


            print
            print('Tag(s) written successfully!')
            print

            while len(uids) != 0:
                print()
                print('Please remove the book')
                print()
                uids = list(reader.inventory())
                time.sleep(1)

        time.sleep(1)

finally:
    reader.close()
