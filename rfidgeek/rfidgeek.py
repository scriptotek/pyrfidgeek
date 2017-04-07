# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

from __future__ import print_function
import serial
import logging
import re
import pprint
from termcolor import colored
import time
import binascii
from .crc import CRC

logger = logging.getLogger(__name__)

ISO15693 = 'ISO15693'
ISO14443A = 'ISO14443A'
ISO14443B = 'ISO14443B'


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

    def __init__(self, serial_port, serial_baud_rate=115200, serial_stop_bits=serial.STOPBITS_ONE,
                 serial_parity=serial.PARITY_NONE, serial_data_bits=serial.EIGHTBITS, debug=False):

        self.protocol = None

        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        self.sp = serial.Serial(port=serial_port,
                                baudrate=serial_baud_rate,
                                stopbits=serial_stop_bits,
                                parity=serial_parity,
                                bytesize=serial_data_bits,
                                timeout=0.1)

        if not self.sp:
            raise StandardError('Could not connect to serial port ' + serial_port)

        logger.debug('Connected to ' + self.sp.portstr)
        self.flush()

    def set_protocol(self, protocol=ISO15693):

        self.protocol = protocol

        # 1. Initialize reader: 0xFF
        # 0108000304 FF 0000
        self.issue_evm_command(cmd='FF')  # Should return "TRF7970A EVM"

        # self.issue_evm_command(cmd='10', prms='0121')
        # self.issue_evm_command(cmd='10', prms='0021')

        # Select protocol: 15693 with full power
        self.issue_evm_command(cmd='10', prms='00210100')

        # Setting up registers:
        #   0x00 Chip Status Control: Set to 0x21 for full power, 0x31 for half power
        #   0x01 ISO Control: Set to 0x00 for ISO15693, 0x09 for ISO14443A, 0x0C for ISO14443B
        protocol_values = {
            ISO15693: '00',   # 01 for 1-out-of-256 modulation
            ISO14443A: '09',
            ISO14443B: '0C',
        }
        self.issue_evm_command(cmd='10', prms='0021' + '01' + protocol_values[protocol])

        # 3. AGC selection (0xF0) : AGC enable (0x00)
        # 0109000304 F0 00 0000
        self.issue_evm_command(cmd='F0', prms='00')

        # 4. AM/PM input selection (0xF1) : AM input (0xFF)
        # 0109000304 F1 FF 0000
        self.issue_evm_command(cmd='F1', prms='FF')

    def enable_led(self, led_no):
        cmd_codes = {2: 'FB', 3: 'F9', 4: 'F7', 5: 'F5', 6: 'F3'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def disable_led(self, led_no):
        cmd_codes = {2: 'FC', 3: 'FA', 4: 'F8', 5: 'F6', 6: 'F4'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def inventory(self, **kwargs):
        if self.protocol == ISO15693:
            return self.inventory_iso15693(**kwargs)
        elif self.protocol == ISO14443A:
            return self.inventory_iso14443A(**kwargs)

    def inventory_iso14443A(self):
        """
        By sending a 0xA0 command to the EVM module, the module will carry out
        the whole ISO14443 anti-collision procedure and return the tags found.

            >>> Req type A (0x26)
            <<< ATQA (0x04 0x00)
            >>> Select all (0x93, 0x20)
            <<< UID + BCC

        """
        response = self.issue_evm_command(cmd='A0')

        for itm in response:
            iba = bytearray.fromhex(itm)
            # Assume 4-byte UID + 1 byte Block Check Character (BCC)
            if len(iba) != 5:
                logger.warn('Encountered tag with UID of unknown length')
                continue
            if iba[0] ^ iba[1] ^ iba[2] ^ iba[3] ^ iba[4] != 0:
                logger.warn('BCC check failed for tag')
                continue
            uid = itm[:8]  # hex string, so each byte is two chars

            logger.debug('Found tag: %s (%s) ', uid, itm[8:])
            yield uid

            # See https://github.com/nfc-tools/libnfc/blob/master/examples/nfc-anticol.c

    def inventory_iso15693(self, single_slot=False):
        # Command code 0x01: ISO 15693 Inventory request
        # Example: 010B000304 14 24 0100 0000
        response = self.issue_iso15693_command(cmd='14',
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
        response = self.issue_iso15693_command(cmd='18',
                                      flags=flagsbyte(address=True),  # 32 (dec) <-> 20 (hex)
                                      command_code='23',
                                      data=uid + '%02X%02X' % (block_offset, number_of_blocks))

        response = response[0]
        if response == 'z':
            return {'error': 'tag-conflict'}
        elif response == '':
            return {'error': 'read-failed'}

        response = [response[i:i+2] for i in range(2, len(response), 2)]

        if response[0] == '00':
            is_blank = True
        else:
            is_blank = False

        # Reference:
        # RFID Data model for libraries : Doc 067 (July 2005), p. 30
        # <http://www.biblev.no/RFID/dansk_rfid_datamodel.pdf>

        # RFID Data model for libraries (February 2009), p. 30
        # http://biblstandard.dk/rfid/dk/RFID_Data_Model_for_Libraries_February_2009.pdf
        version = response[0][0]    # not sure if this is really the way to do it
        if version != '0' and version != '1':
            print(response)
            return {'error': 'unknown-version: %s' % version}

        usage_type = {
            '0': 'acquisition',
            '1': 'for-circulation',
            '2': 'not-for-circulation',
            '7': 'discarded',
            '8': 'patron-card'
        }[response[0][1]]  # not sure if this is really the way to do it

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
            'error': '',
            'is_blank': is_blank,
            'usage_type': usage_type,
            'uid': uid,
            'id': itemid.strip('\0'),
            'partno': partno,
            'nparts': nparts,
            'country': country,
            'library': library.strip('\0'),
            'crc': crc,
            'crc_ok': calc_crc == crc
        }


    def write_danish_model_tag(self, uid, data, max_attempts=20):
        block_number = 0
        blocks = []

        data_bytes = ['00' for x in range(32)]
        data_bytes[0] = '11'
        data_bytes[1] = '%02X' % data['partno']
        data_bytes[2] = '%02X' % data['nparts']
        dokid = ['%02X' % ord(c) for c in data['id']]
        data_bytes[3:3+len(dokid)] = dokid
        data_bytes[21:23] = ['%02X' % ord(c) for c in data['country']]
        libnr = ['%02X' % ord(c) for c in data['library']]
        data_bytes[23:23+len(libnr)] = libnr

        # CRC calculation:
        p1 = data_bytes[0:19]     # 19 bytes
        p2 = data_bytes[21:32]    # 11 bytes
        p3 = ['00', '00']       # need to add 2 empty bytes to get 19 + 13 bytes
        p = [int(x, 16) for x in p1 + p2 + p3]
        crc = CRC().calculate(p)[::-1]
        data_bytes[19:21] = crc

        print(data_bytes)

        for x in range(8):
            print(data_bytes[x*4:x*4+4])
            attempt = 1
            while not self.write_block(uid, x, data_bytes[x*4:x*4+4]):
                logger.warn('Attempt %d of %d: Write failed, retrying...' % (attempt, max_attempts))
                if attempt >= max_attempts:
                    return False
                else:
                    attempt += 1
                    time.sleep(1.0)
        return True

    def write_blocks_to_card(self, uid, data_bytes, offset=0, nblocks=8):
        for x in range(offset, nblocks):
            print(data_bytes[x*4:x*4+4])
            success = False
            attempts = 0
            max_attempts = 10
            while not success:
                attempts += 1
                success = self.write_block(uid, x, data_bytes[x*4:x*4+4])
                if not success:
                    logger.warn('Write failed, retrying')
                    if attempts > max_attempts:
                        logger.warn('Giving up!')
                        return False
                    #time.sleep(1.0)
        return True

    def erase_card(self, uid):
        data_bytes = ['00' for x in range(32)]
        return self.write_blocks_to_card(uid, data_bytes)

    def write_danish_model_patron_card(self, uid, data):
        block_number = 0
        blocks = []

        data_bytes = ['00' for x in range(32)]

        version = '1'
        usage_type = '8'
        data_bytes[0] = version + usage_type
        data_bytes[1] = '01'  # partno
        data_bytes[2] = '01'  # nparts
        userid = ['%02X' % ord(c) for c in data['user_id']]
        print('userid:', userid)
        data_bytes[3:3+len(userid)] = userid
        data_bytes[21:23] = ['%02X' % ord(c) for c in data['country']]
        libnr = ['%02X' % ord(c) for c in data['library']]
        data_bytes[23:23+len(libnr)] = libnr

        # CRC calculation:
        p1 = data_bytes[0:19]     # 19 bytes
        p2 = data_bytes[21:32]    # 11 bytes
        p3 = ['00', '00']       # need to add 2 empty bytes to get 19 + 13 bytes
        p = [int(x, 16) for x in p1 + p2 + p3]
        crc = CRC().calculate(p)[::-1]
        data_bytes[19:21] = crc

        print(data_bytes)

        return self.write_blocks_to_card(uid, data_bytes)

    def write_block(self, uid, block_number, data):
        if type(data) != list or len(data) != 4:
            raise StandardError('write_block got data of unknown type/length')

        response = self.issue_iso15693_command(cmd='18',
                                      flags=flagsbyte(address=True),  # 32 (dec) <-> 20 (hex)
                                      command_code='21',
                                      data='%s%02X%s' % (uid, block_number, ''.join(data)))
        if response[0] == '00':
            logger.debug('Wrote block %d successfully', block_number)
            return True
        else:
            return False


    def unlock_afi(self, uid):
        self.issue_iso15693_command(cmd='18',
                           flags=flagsbyte(address=False,
                                           high_data_rate=True,
                                           option=False),  # 32 (dec) <-> 20 (hex)
                           command_code='27',
                           data='C2')

    def lock_afi(self, uid):
        self.issue_iso15693_command(cmd='18',
                           flags=flagsbyte(address=False,
                                           high_data_rate=False,
                                           option=False),  # 32 (dec) <-> 20 (hex)
                           command_code='27',
                           data='07')

    def issue_evm_command(self, cmd, prms=''):
        # The EVM protocol has a general form as shown below:
        #  1. SOF (Start of File): 0x01
        #  2. LENGTH : Two bytes define the number of bytes in the frame including SOF. Least Significant Byte first!
        #  3. READER_TYPE : 0x03
        #  4. ENTITY : 0x04
        #  5. CMD : The command
        #  6. PRMS : Parameters
        #  7. EOF : 0x0000

        # Two-digit hex strings (without 0x prefix)
        sof = '01'
        reader_type = '03'
        entity = '04'
        eof = '0000'

        result = reader_type + entity + cmd + prms + eof

        length = int(len(result)/2) + 3  # Number of *bytes*, + 3 to include SOF and LENGTH
        length = '%04X' % length  # Convert int to hex
        length = binascii.unhexlify(length)[::-1]  # Reverse hex string to get LSB first
        length = binascii.hexlify(length).decode('ascii')

        result = sof + length + result

        self.write(result)
        response = self.read()
        return self.get_response(response)

    def issue_iso15693_command(self, cmd, flags='', command_code='', data=''):
        return self.issue_evm_command(cmd, flags + command_code + data)

    def flush(self):
        self.sp.readall()

    def write(self, msg):
        logger.debug('SEND%3d: ' % (len(msg)/2) + msg[0:10] + colored(msg[10:12], attrs=['underline']) + msg[12:14] + colored(msg[14:], 'green'))
        self.sp.write(msg.encode('ascii'))

    def read(self):
        msg = self.sp.readall()
        logger.debug('RETR%3d: ' % (len(msg)/2) + colored(pprint.saferepr(msg).strip("'"), 'cyan'))
        return msg

    def get_response(self, response):
        return re.findall(r'\[(.*?)\]', response.decode('ascii'))

    def close(self):
        self.sp.close()

