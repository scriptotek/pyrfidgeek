#!/usr/bin/python
import logging
import threading
import Queue
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

active_queues = []


class WebSocketHandler(logging.StreamHandler):
    """
    A handler class which emits messages to a websocket
    """

    def __init__(self, socket):
        logging.StreamHandler.__init__(self)
        self.websocket = socket

    def emit(self, record):
        try:
            msg = self.format(record)
            self.websocket.send(json.dumps({
                'rcpt': 'frontend',
                'msg': 'log-msg',
                'text': msg
            }))
        except:
            self.handleError(record)


class ScannerThread(threading.Thread):
    """
    Inventory scan loop thread
    """

    def __init__(self, rfid, ws, parent_mailbox):
        super(ScannerThread, self).__init__()
        self.rfid = rfid
        self.ws = ws
        self.scanning = False
        self.paused = False
        self.mailbox = Queue.Queue()
        self.parent_mailbox = parent_mailbox
        active_queues.append(self.mailbox)

    def join(self, timeout=None):
        self.stoprequest.set()
        super(WorkerThread, self).join(timeout)

    def pause(self): 
        self.paused = True

    def cont(self):
        self.paused = False

    # def write_patron_card(self, uid, data):
    #     print 'WRITE IT!!!', uid
    #         reader.write_danish_model_patron_card(message['uid'], {
    #             'user_id': message['data']['user_id'],
    #             'library': '1030310',
    #             'country': 'NO'
    #         })

    def stop(self):
        active_queues.remove(self.mailbox)
        self.mailbox.put('shutdown')
        self.join()

    def run(self):
        ws = self.ws

        # Start by saying hello 
        ws.send(json.dumps({
            'msg': 'hello',
            'role': 'backend'
        }))

        try:

            uids = {}
            prev_uids = [{}, {}]

            logger.info('Scanning for tags')

            while True:
                if not self.mailbox.empty():
                    data = self.mailbox.get()
                    if data == 'shutdown':
                        print self, 'Shutting down inventory scan'
                        return
                    elif data == 'pause':
                        self.paused = True
                        logger.info('Pausing inventory scan')
                        self.parent_mailbox.put('paused')
                    elif data == 'cont':
                        self.paused = False
                        logger.info('Continuing inventory scan')
                    print self, 'received a message', data

                uids = {}
                if not self.paused:
                    self.scanning = True
                    for uid in rfid.inventory():
                        uids[uid] = 'unknown'
                        if uid in prev_uids[0]:
                            uids[uid] = prev_uids[0][uid]
                        elif uid in prev_uids[1]:
                            uids[uid] = prev_uids[1][uid]

                    for uid, oid in uids.items():

                        if oid == 'unknown':
                            #if not uid in prev_uids[0] and not uid in prev_uids[1]:
                            item = rfid.read_danish_model_tag(uid)
                            if item['error'] != '':
                                #logger.warn(item['error'])
                                pass
                            else:

                                if item['is_blank']:
                                    logger.info('Blank tag found')
                                    ws.send(json.dumps({
                                        'rcpt': 'frontend',
                                        'msg': 'new-tag',
                                        'item': item,
                                        'uid': uid
                                    }))
                                    uids[uid] = 'blank'

                                elif 'id' in item:
                                    oid = item['id']
                                    if not oid in uids.values():
                                        logger.info('Tag found of type %s: %s' % (item['usage_type'], item['id']))
                                        ws.send(json.dumps({
                                            'rcpt': 'frontend',
                                            'msg': 'new-tag',
                                            'item': item,
                                            'uid': uid
                                        }))
                                    uids[uid] = oid

                    prev_uids[1] = copy(prev_uids[0])
                    prev_uids[0] = copy(uids)
                self.scanning = False
                time.sleep(0.5)

        finally:
            rfid.close()

        time.sleep(1)
        ws.close()

        print "thread terminating..."


rfid = PyRFIDGeek(config)


class WsSock(object):

    def __init__(self):
        logger.info('Trying to connect to labs.biblionaut.net:8080')
        self.ws = websocket.WebSocketApp('ws://labs.biblionaut.net:8080',
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close)
        self.ws.on_open = self.on_open
        self.mailbox = Queue.Queue()

    def start(self):
        self.ws.run_forever()

    def on_message(self, ws, message):
        message = json.loads(message)
        logger.info('Got patron card write request from ws frontend client')
        queue = active_queues[0]

        # Tell inventory scan thread to pause (while writing)
        queue.put('pause')

        time.sleep(0.5)

        if not self.mailbox.empty():
            data = self.mailbox.get()
            if data == 'paused':
                logger.info('Inventory scan thread paused')

        # scanner.on('paused', function () {
        # if message['msg'] == 'write-patron-card':
        #     self.scanner.pause()

        ws.send(json.dumps({
            'rcpt': 'frontend',
            'msg': 'writing-card',
            'uid': message['uid']
        }))

        rfid.enable_led(5)
        rfid.write_danish_model_patron_card(message['uid'], {
            'user_id': message['data']['user_id'],
            'library': '1030310',
            'country': 'NO'
        })
        rfid.disable_led(5)

        # Tell inventory scan thread to continue
        queue.put('cont')
        self.ws.send(json.dumps({
            'rcpt': 'frontend',
            'msg': 'card-written',
            'user_id': message['data']['user_id']
        }))

    def attach_websocket_logger(self):
        wh = WebSocketHandler(self.ws)
        wh.setLevel(logging.INFO)
        #logger.addHandler(wh)

    def on_error(self, ws, error):
        logger.error(error)

    def on_close(self, ws):
        logger.info("websocket closed")

    def on_open(self, ws):
        self.attach_websocket_logger()
        self.scanner = ScannerThread(rfid, ws, self.mailbox)
        self.scanner.start()
        #thread.start_new_thread(run, (ws,))

if __name__ == "__main__":

    websocket.enableTrace(True)
    s = WsSock()
    s.start()
