# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*- 
# vim:fenc=utf-8:et:sw=4:ts=4:sts=4:tw=0
#
# The CRC is calculated using x^16 + x^12 + x^5 + 1 polynomial with hex (ffff) as start value
#
# The CRC will be calculated starting from the lowest address, first 19 bytes, then 
# skipping the two CRC bytes, then 13 bytes for a total of 32 bytes (For chips with 32 
# data bytes only the last two bytes are assumed to be chr(0), see chapter 3.2.1.8 Owner 
# library)
#
# Reference:
# RFID Data model for libraries : Doc 067 (July 2005), p. 51
# <http://www.biblev.no/RFID/dansk_rfid_datamodel.pdf>


class CRC(object):

    def __init__(self):
        pass

    def calculate(self, s):
        self.crc_poly=0x1021
        self.crc_sum=0xffff
        for c in s:
            self.update_crc(c)
        r = '%02X' % self.crc_sum
        return [r[i:i+2] for i in range(0, len(r), 2)] 

    def update_crc(self, c):
        c <<= 8
        for i in range(0,8):
            xor_flag = ((self.crc_sum ^ c) & 0x8000) != 0
            self.crc_sum = self.crc_sum << 1
            if xor_flag:
                self.crc_sum = self.crc_sum ^ self.crc_poly
            c = c << 1
        self.crc_sum &= 0xffff

if __name__ == '__main__':
    # Test that should return 1AEE
    x = [ord(x) for x in 'RFID tag data model']
    print(CRC().calculate(x))

