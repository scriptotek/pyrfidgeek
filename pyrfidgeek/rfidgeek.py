# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0
#

import serial
import logging
import re
import pprint
from termcolor import colored

from crc import CRC

logger = logging.getLogger()


def flagsbyte(double_sub_carrier=False, high_data_rate=False, inventory=False,
              protocol_extension=False, afi=False, single_slot=False,
              option=False, select=False, address=False):
    # Method to construct the flags byte
    # Reference: TI TRF9770A Evaluation Module (EVM) User's Guide, p. 8
    #            <http://www.ti.com/litv/pdf/slou321a>
    bits = '0'                                  # bit 8 (RFU) is always zero
    bits += '1' if option else '0'              # bit 7
    if inventory:
        bits += '1' if single_slot else '0'     # bit 6
        bits += '1' if afi else '0'             # bit 5
    else:
        bits += '1' if address else '0'         # bit 6
        bits += '1' if select else '0'          # bit 5
    bits += '1' if protocol_extension else '0'  # bit 4
    bits += '1' if inventory else '0'           # bit 3
    bits += '1' if high_data_rate else '0'      # bit 2
    bits += '1' if double_sub_carrier else '0'  # bit 1

    return '%02X' % int(bits, 2)     # return hex byte


class PyRFIDGeek(object):

    def __init__(self, config):

        self.config = config
        if config['debug']:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        self.sp = serial.Serial(port=self.config['serial']['port'],
                                baudrate=self.config['serial']['baud_rate'],
                                stopbits=self.config['serial']['stop_bits'],
                                parity=self.config['serial']['parity'],
                                timeout=0.1)

        if not self.sp:
            raise StandardError('Could not connect to serial port '
                                + self.config['serial']['port'])

        logger.debug('Connected to ' + self.sp.portstr)
        self.flush()

        # Initialize reader: 0xFF
        # 0108000304 FF 0000
        self.issue_command(cmd='FF')

        # Register write request: 0x10
        # 010A000304 10 01 21 0000
        # 010C000304 10 00 21 0100 0000
        # 010C000304 10 00 21 0100 0000
        self.issue_command(cmd='10', flags='00', command_code='21', data='0100')

        # Enable AGC: 0xF0
        # 0109000304 F0 00 0000
        self.issue_command(cmd='F0')

        # AM input: 0xF1
        # 0109000304 F1 FF 0000
        self.issue_command(cmd='F1', flags='FF')

    def enable_led(self, led_no):
        cmd_codes = {2: 'FB', 3: 'F9', 4: 'F7', 5: 'F5', 6: 'F3'}
        self.issue_command(cmd=cmd_codes[led_no])

    def disable_led(self, led_no):
        cmd_codes = {2: 'FC', 3: 'FA', 4: 'F8', 5: 'F6', 6: 'F4'}
        self.issue_command(cmd=cmd_codes[led_no])

    def inventory(self, single_slot=False):
        # Command code 0x01: ISO 15693 Inventory request
        # Example: 010B000304 14 24 0100 0000
        response = self.issue_command(cmd='14',         # ??
                                      flags=flagsbyte(inventory=True,
                                                      single_slot=single_slot),
                                      command_code='01',
                                      data='00')
        for itm in response:
            itm = itm.split(',')
            if itm[0] == 'z':
                logger.debug('Tag conflict!')
            else:
                if len(itm[0]) == 16:
                    uid = itm[0]
                    logger.debug('Found tag: %s (%s) ', uid, itm[1])
                    yield uid

    def read_danish_model_tag(self, uid):
        # Command code 0x23: Read multiple blocks
        block_offset = 0
        number_of_blocks = 8
        response = self.issue_command(cmd='18',
                                      flags=flagsbyte(address=True),  # 32 (dec) <-> 20 (hex)
                                      command_code='23',
                                      data=uid + '%02X%02X' % (block_offset, number_of_blocks))
        response = response[0]
        response = [response[i:i+2] for i in range(2, len(response), 2)]

        # Reference:
        # RFID Data model for libraries : Doc 067 (July 2005), p. 30
        # <http://www.biblev.no/RFID/dansk_rfid_datamodel.pdf>
        nparts = int(response[1], 16)
        partno = int(response[2], 16)
        itemid = ''.join([chr(int(x, 16)) for x in response[3:19]])
        crc = response[19:21]
        country = ''.join([chr(int(x, 16)) for x in response[21:23]])
        library = ''.join([chr(int(x, 16)) for x in response[23:32]])

        # CRC calculation:
        p1 = response[0:19]     # 19 bytes
        p2 = response[21:32]    # 11 bytes
        p3 = ['00', '00']       # need to add 2 empty bytes to get 19 + 13 bytes
        p = [int(x, 16) for x in p1 + p2 + p3]
        calc_crc = ''.join(CRC().calculate(p)[::-1])
        crc = ''.join(crc)

        return {
            'uid': uid,
            'id': itemid,
            'partno': partno,
            'nparts': nparts,
            'country': country,
            'library': library,
            'crc': crc,
            'crc_ok': calc_crc == crc
        }

    def write_danish_model_tag(self, uid, data):
        block_number = 0
        blocks = []

        data_bytes = ['FF' for x in range(32)]
        data_bytes[0] = '11'
        data_bytes[1] = '%01X' % data['partno']
        data_bytes[2] = '%01X' % data['nparts']
        dokid = ['%.2X' % ord(c) for c in data['id']]
        data_bytes[3:3+len(dokid)] = dokid
        data_bytes[21:23] = ['%.2X' % ord(c) for c in data['country']]
        libnr = ['%.2X' % ord(c) for c in data['library']]
        data_bytes[23:23+len(libnr)] = libnr

        # CRC calculation:
        p1 = data_bytes[0:19]     # 19 bytes
        p2 = data_bytes[21:32]    # 11 bytes
        p3 = ['00', '00']       # need to add 2 empty bytes to get 19 + 13 bytes
        p = [int(x, 16) for x in p1 + p2 + p3]
        crc = ''.join(CRC().calculate(p)[::-1])
        data_bytes[19:21] = crc

        for x in range(8):
            if not write_block(x, data_bytes[x*8:x*8+4]):
                return False
        return True

    def write_block(block_number, data):
        if type(data) != list or len(data) != 4:
            raise StandardError('write_block got data of unknown type/length')

        response = self.issue_command(cmd='18',
                                      flags=flagsbyte(address=True),  # 32 (dec) <-> 20 (hex)
                                      command_code='21',
                                      data='%s%02X%s' % (uid, block_number, ''.join(data)))
        if response[0] == '00':
            logger.debug('Wrote block %d successfully', block_number)
            return True
        else:
            return False


    def unlock_afi(self, uid):
        self.issue_command(cmd='18',
                           flags=flagsbyte(address=False,
                                           high_data_rate=True,
                                           option=False),  # 32 (dec) <-> 20 (hex)
                           command_code='27',
                           data='C2')

    def lock_afi(self, uid):
        self.issue_command(cmd='18',
                           flags=flagsbyte(address=False,
                                           high_data_rate=False,
                                           option=False),  # 32 (dec) <-> 20 (hex)
                           command_code='27',
                           data='07')

    def issue_command(self, cmd, flags='', command_code='', data=''):
        # The communication starts with SOF (0x01).
        # The second byte defines the number of bytes in the frame including SOF.
        # The third byte should be kept at 0x00, fourth byte at 0x03 and the fifth byte at 0x04.
        # The sixth byte is the command code, which is followed by parameters or data.
        # The communication ends with 2 bytes of 0x00.

        cmd = '000304' + cmd + flags + command_code + data + '0000'
        cmd_len = 2 + len(cmd)/2   # number of bytes
        cmd_len_hex = '%0.2X' % cmd_len
        cmd = '01' + cmd_len_hex + cmd

        self.write(cmd)
        response = self.read()
        return self.get_response(response)

    def flush(self):
        self.sp.readall()

    def write(self, msg):
        logger.debug('SEND(%2d): ' % len(msg)/2 + colored('%s %s %s %s' % (msg[0:10], msg[10:12], msg[12:14], msg[14:]), 'green'))
        self.sp.write(msg)

    def read(self):
        msg = self.sp.readall()
        logger.debug('RETR(%3d): ' % len(msg)/2 + colored(pprint.saferepr(msg), 'brown'))
        return msg

    def get_response(self, response):
        return re.findall(r'\[(.+?)\]', response)

    def close(self):
        self.sp.close()

