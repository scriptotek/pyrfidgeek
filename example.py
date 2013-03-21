#encoding=utf-8

import logging
import argparse
import yaml

from pyrfidgeek import PyRFIDGeek

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek')
parser.add_argument('--config', nargs='?', default='config.yml',
                    help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

reader = PyRFIDGeek(config)

for uid in reader.inventory():
    item = reader.read_tag_danish_model(uid)
    print
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

    reader.unlock_afi(uid)

reader.close()
