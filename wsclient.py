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


class ScannerThread(threading.Thread):

    def __init__(self, rfid, ws):
        super(ScannerThread, self).__init__()
        self.rfid = rfid
        self.ws = ws
        self.scanning = False
        self.paused = False
        self.mailbox = Queue.Queue()
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
        self.mailbox.put("shutdown")
        self.join()

    def run(self):
        ws = self.ws

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
                        print self, 'shutting down'
                        return
                    elif data == 'pause':
                        self.paused = True
                        logger.info('Puased')
                    elif data == 'cont':
                        self.paused = False
                        logger.info('Continue')
                    print self, 'received a message', data

                uids = {}
                if not self.paused:
                    self.scanning = True
                    for uid in rfid.inventory():
                        uids[uid] = ''
                        if uid in prev_uids[0]:
                            uids[uid] = prev_uids[0][uid]
                        elif uid in prev_uids[1]:
                            uids[uid] = prev_uids[1][uid]

                    for uid, oid in uids.items():

                        if oid == '':
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
                                        'msg': 'blank-tag',
                                        'uid': uid
                                    }))

                                elif 'id' in item:
                                    oid = item['id']
                                    if not oid in uids.values():
                                        logger.info('Tag found: %s' % item['id'])
                                        ws.send(json.dumps({
                                            'rcpt': 'frontend',
                                            'msg': 'new-item',
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
        self.ws = websocket.WebSocketApp('ws://labs.biblionaut.net:8080',
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close)
        self.ws.on_open = self.on_open

    def start(self):
        self.ws.run_forever()

    def on_message(self, ws, message):
        message = json.loads(message)
        logger.info('Got patron card write request from ws frontend client')
        for q in active_queues:
            q.put('pause')
            time.sleep(0.5)

            # scanner.on('paused', function () {
            # if message['msg'] == 'write-patron-card':
            #     self.scanner.pause()

            ws.send(json.dumps({
                'rcpt': 'frontend',
                'msg': 'writing-card',
                'uid': message['uid']
            }))

            rfid.write_danish_model_patron_card(message['uid'], {
                'user_id': message['data']['user_id'],
                'library': '1030310',
                'country': 'NO'
            })
            q.put('cont')
            self.ws.send(json.dumps({
                'rcpt': 'frontend',
                'msg': 'card-written',
                'user_id': message['data']['user_id']
            }))

    def on_error(self, ws, error):
        logger.error(error)

    def on_close(self, ws):
        logger.debug("### closed ###")

    def on_open(self, ws):
        self.scanner = ScannerThread(rfid, ws)
        self.scanner.start()
        #thread.start_new_thread(run, (ws,))

if __name__ == "__main__":

    websocket.enableTrace(True)
    s = WsSock()
    s.start()
