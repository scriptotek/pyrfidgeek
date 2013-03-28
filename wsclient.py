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
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

parser = argparse.ArgumentParser(description='PyRfidGeek reader example')
parser.add_argument('--config', nargs='?', default='config.yml',
                    help='Config file')
args = parser.parse_args()
config = yaml.load(open(args.config, 'r'))

reader = PyRFIDGeek(config)

def on_message(ws, message):
    logger.info(message)

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

            uids = []
            current_uids = []
            while True:
                uids = list(reader.inventory())
                for uid in uids:

                    if not uid in current_uids:
                        item = reader.read_danish_model_tag(uid)
                        ws.send(json.dumps({
                            'msg': 'new-item',
                            'itemid': item['id']
                        }))

                current_uids = copy(uids)
                #time.sleep(1)

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
