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
ch.setLevel(logging.INFO)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek reader example')
parser.add_argument('--config', nargs='?', default='config.yml',
                    help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

reader = PyRFIDGeek(config)

try:

    uids = []
    prev_uids = [[], []]
    while True:
        uids = list(reader.inventory())
        successful_reads = []
        print '%d tags' % len(uids)
        for uid in uids:

            if not uid in prev_uids[0] and not uid in prev_uids[1]:  # and not uid in prev_uids[2]:
                item = reader.read_danish_model_tag(uid)
                if item['error'] != '':
                    print 'error reading tag: ',item['error']
                else:
                    if item['is_blank']:
                        print ' Found blank tag'

                    elif 'id' in item:
                        print
                        print ' Found new tag, usage type: %s' % item['usage_type']
                        print ' # Item id: %s (part %d of %d)' % (item['id'],
                                                                  item['partno'],
                                                                  item['nparts'])
                        print '   Country: %s, library: %s' % (item['country'],
                                                               item['library'])
                        if item['crc_ok']:
                            print '   CRC check successful'
                            successful_reads.append(uid)
                        else:
                            print '   CRC check failed'

            #reader.unlock_afi(uid)

        #prev_uids[2] = copy(prev_uids[1])
        prev_uids[1] = copy(prev_uids[0])
        prev_uids[0] = copy(uids)

        time.sleep(1)

finally:
    reader.close()
