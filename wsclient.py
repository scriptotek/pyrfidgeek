#!/usr/bin/python
import logging
import thread
import time
import json
import websocket
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

def on_message(ws, message):
    logger.info(message)
    if message['msg'] == 'write-patron-card':
        person_data = message['data']
        reader.write_danish_model_patron_card({
            'user_id': persondata['user_id'],
            'library': '1030310',
            'country': 'NO'
        })

def on_error(ws, error):
    logger.error(error)

def on_close(ws):
    logger.debug("### closed ###")

def on_open(ws):
    def run(*args):

        ws.send(json.dumps({
            'msg': 'hello',
            'role': 'backend'
        }))

        try:

            uids = {}
            prev_uids = [{}, {}]

            logger.info('Scanning for tags')

            while True:
                uids = {}
                for uid in reader.inventory():
                    uids[uid] = ''
                    if uid in prev_uids[0]:
                        uids[uid] = prev_uids[0][uid]
                    elif uid in prev_uids[1]:
                        uids[uid] = prev_uids[1][uid]

                for uid, oid in uids.items():

                    if oid == '':
                        #if not uid in prev_uids[0] and not uid in prev_uids[1]:
                        item = reader.read_danish_model_tag(uid)
                        if item['error'] == '':

                            if item['is_blank']:
                                logger.info('Blank tag found')
                                ws.send(json.dumps({
                                    'msg': 'blank-tag',
                                    'uid': uid
                                }))

                            elif 'id' in item:
                                oid = item['id']
                                if not oid in uids.values():
                                    logger.info('Tag found: %s' % item['id'])
                                    ws.send(json.dumps({
                                        'msg': 'new-item',
                                        'itemid': item['id'],
                                        'uid': uid
                                    }))
                                uids[uid] = oid

                prev_uids[1] = copy(prev_uids[0])
                prev_uids[0] = copy(uids)
                time.sleep(0.5)

        finally:
            reader.close()

        time.sleep(1)
        ws.close()

        print "thread terminating..."

    thread.start_new_thread(run, ())


if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp('ws://labs.biblionaut.net:8080',
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open

    ws.run_forever()
