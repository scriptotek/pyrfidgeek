# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0

import serial
import logging
import re
import pprint
from termcolor import colored
from crc import CRC
import time
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
        self.issue_iso15693_command(cmd='FF')

        # Register write request: 0x10
        # 010A000304 10 01 21 0000
        # 010C000304 10 00 21 0100 0000
        # 010C000304 10 00 21 0100 0000
        self.issue_iso15693_command(cmd='10', flags='00', command_code='21')

        # Register write request: 0x10
        # 010A000304 10 01 21 0000
        # 010C000304 10 00 21 0100 0000
        # 010C000304 10 00 21 0100 0000
        self.issue_iso15693_command(cmd='10', flags='00', command_code='21', data='0100')

        # Enable AGC: 0xF0
        # 0109000304 F0 00 0000
        self.issue_iso15693_command(cmd='F0')

        # AM input: 0xF1
        # 0109000304 F1 FF 0000
        self.issue_iso15693_command(cmd='F1', flags='FF')

    def enable_led(self, led_no):
        cmd_codes = {2: 'FB', 3: 'F9', 4: 'F7', 5: 'F5', 6: 'F3'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def disable_led(self, led_no):
        cmd_codes = {2: 'FC', 3: 'FA', 4: 'F8', 5: 'F6', 6: 'F4'}
        self.issue_iso15693_command(cmd=cmd_codes[led_no])

    def inventory(self, single_slot=False):
        # Command code 0x01: ISO 15693 Inventory request
        # Example: 010B000304 14 24 0100 0000
        response = self.issue_iso15693_command(cmd='14',         # ??
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
            print response
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

        print data_bytes

        for x in range(8):
            print data_bytes[x*4:x*4+4]
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
            print data_bytes[x*4:x*4+4]
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
        print 'userid:', userid
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

        print data_bytes

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

        length = len(result)/2 + 3  # Number of *bytes*, + 3 to include SOF and LENGTH
        length = '%04X' % length  # Convert int to hex
        length = length.decode('hex')[::-1].encode('hex').upper()  # Reverse hex string to get LSB first
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
        self.sp.write(msg)

    def read(self):
        msg = self.sp.readall()
        logger.debug('RETR%3d: ' % (len(msg)/2) + colored(pprint.saferepr(msg).strip("'"), 'cyan'))
        return msg

    def get_response(self, response):
        return re.findall(r'\[(.*?)\]', response)

    def close(self):
        self.sp.close()

