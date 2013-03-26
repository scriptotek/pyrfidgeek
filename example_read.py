# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

import logging
import argparse
import yaml
import time
from copy import copy

from pyrfidgeek import PyRFIDGeek

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek reader example')
parser.add_argument('--config', nargs='?', default='config.yml',
                    help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

reader = PyRFIDGeek(config)

try:

    uids = []
    while True:
        uids = list(reader.inventory())
        for uid in uids:

            if not uid in current_uids:
                item = reader.read_danish_model_tag(uid)
                print
                print ' Found new tag'
                print ' # Item id: %s (part %d of %d)' % (item['id'],
                                                          item['partno'],
                                                          item['nparts'])
                print '   Country: %s, library: %s' % (item['country'],
                                                       item['library'])
                if item['crc_ok']:
                    print '   CRC check successful'
                else:
                    print '   CRC check failed'
                print

            #reader.unlock_afi(uid)

        current_uids = copy(uids)

        time.sleep(1)

finally:
    reader.close()
