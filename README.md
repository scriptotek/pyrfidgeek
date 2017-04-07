**PyRFIDGeek** is a python package for reading and writing ISO 15693 cards following the Danish
RFID data model for libraries, using serial communication to [RFIDGeek](http://rfidgeek.com/)
boards (tested with RFIDUARTUSB7970 from RFIDGeek) and possibly other boards based on the
[TI TRF7970A chip](http://www.ti.com/product/trf7970A), such as
[TI's Evaluation Module](http://www.ti.com/tool/trf7970aevm) (EVM). In addition, it can
scan for ISO14443A/B cards and return their UIDs, but there's no read/write support for
ISO14443 or Mifare (pull requests are welcome :))

## Examples

*See also the `example_*.py` files.*


### Scanning for ISO 14443 and 15693 tags:

```python
import yaml
from rfidgeek import PyRFIDGeek, ISO14443A, ISO15693
config = yaml.load(open('config.yml', 'r'))
reader = PyRFIDGeek(config)

for protocol in [ISO14443A, ISO15693]:
    reader.set_protocol(protocol)
    for uid in reader.inventory():
        print('Found {} tag: {}', protocol, uid)

reader.close()
```

### Reading ISO 15693 tags

```python
import yaml
from rfidgeek import PyRFIDGeek, ISO15693
config = yaml.load(open('config.yml', 'r'))
reader = PyRFIDGeek(config)
reader.set_protocol(ISO15693)
for uid in reader.inventory(single_slot=False):
    item = reader.read_danish_model_tag(uid)
    print
    print ' # Item id: %s (part %d of %d)' % (item['id'], item['partno'], item['nparts'])
    print '   Country: %s, library: %s' % (item['country'], item['library'])
    if item['crc_ok']:
        print '   CRC check successful'
    else:
        print '   CRC check failed'
    print
reader.close()
```

### Writing ISO 15693 tags

```python
import yaml
from rfidgeek import PyRFIDGeek, ISO15693

config = yaml.load(open('config.yml', 'r'))
rfid = PyRFIDGeek(config)
reader.set_protocol(ISO15693)
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

