from __future__ import print_function
import yaml
from rfidgeek import PyRFIDGeek, ISO14443A, ISO15693

# You might need to change this:
COM_PORT_NAME='/dev/tty.SLAB_USBtoUART'

reader = PyRFIDGeek(serial_port=COM_PORT_NAME, debug=True)

protocols = [ISO14443A, ISO15693]

try:
    while True:
        tags = {protocol: set() for protocol in protocols}

        for protocol in protocols:
            reader.set_protocol(protocol)
            for uid in reader.inventory():
                tags[protocol].add(uid)

        tags2 = ['{} ({})'.format(tag, protocol) for protocol in protocols for tag in tags[protocol]]
        total_tags = len(tags[ISO14443A]) + len(tags[ISO15693])

        print('Found %d tag(s): %s' % (total_tags, ', '.join(tags2)))

finally:
    print('Bye!')
    reader.close()
