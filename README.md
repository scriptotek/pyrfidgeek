**PyRFIDGeek** is a python package for reading and writing ISO 15693 cards following the Danish
RFID data model for libraries, using serial communication to [RFIDGeek](http://rfidgeek.com/)
boards (tested with RFIDUARTUSB7970 from RFIDGeek) and possibly other boards based on the
[TI TRF7970A chip](http://www.ti.com/product/trf7970A), such as
[TI's Evaluation Module](http://www.ti.com/tool/trf7970aevm) (EVM). In addition, it can
scan for ISO14443A/B cards and return their UIDs, but there's no read/write support for
ISO14443 or Mifare (pull requests are welcome :))

To install from PyPI:

    pip install rfidgeek

## Initialization

If you haven't already, you might need to install the [CP210x
USB to UART Bridge VCP Drivers](http://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers) first.

You then need to find out the name of the virtual com port the RFID board is connected to.
On Mac OS , it's most likely `/dev/tty.SLAB_USBtoUART`. If not, look for similar names
under `/dev/`. On Windows, it will be `COMx`, where `x` is some number. Check device manager
or scan through the ports to find `x`.

Once you have the COM port name, you can initialize PyRFIDGeek like so:

```
from rfidgeek import PyRFIDGeek, ISO14443A, ISO15693

rfid = PyRFIDGeek(serial_port='/dev/tty.SLAB_USBtoUART')
```

There's additional serial port options that can be changed, but most likely the defaults will do fine.

## Examples

*See also the `example_*.py` files.*

### Scanning for ISO 14443 and 15693 tags:

```python
for protocol in [ISO14443A, ISO15693]:
    rfid.set_protocol(protocol)
    for uid in rfid.inventory():
        print('Found {} tag: {}', protocol, uid)

rfid.close()
```

### Reading ISO 15693 tags

```python
rfid.set_protocol(ISO15693)

for uid in rfid.inventory(single_slot=False):
    item = rfid.read_danish_model_tag(uid)
    print
    print ' # Item id: %s (part %d of %d)' % (item['id'], item['partno'], item['nparts'])
    print '   Country: %s, library: %s' % (item['country'], item['library'])
    if item['crc_ok']:
        print '   CRC check successful'
    else:
        print '   CRC check failed'
    print

rfid.close()
```

### Writing ISO 15693 tags

```python
rfid.set_protocol(ISO15693)
uids = rfid.inventory()

for partno, uid in enumerate(uids):
    item = {
        'partno': partno,
        'nparts': len(uids),
        'country': 'NO',
        'library': '1030310',   # ISIL
        'id': '75K110086'       # Document id
    }
    if rfid.write_danish_model_tag(uid, item):
        print 'Wrote tag %d of %d' % (partno, len(uids))
    else:
        print 'Write failed, please try again'

rfid.close()
```

### Debugging

To see all messages sent and received, add a logging handler before you
initialize the RFIDGeek module, such as `StreamHandler` that prints to
stderr by default:

```python
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

...

```

Optionally, install termcolor (`pip install termcolor`) to get
color coded messages.
