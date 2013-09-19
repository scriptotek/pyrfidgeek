**PyRFIDGeek** is a python package for reading and writing cards following the Danish RFID data model for libraries,
using serial communication to [RFIDGeek](http://rfidgeek.com/) boards 
(tested with RFIDUARTUSB7970) and possibly other boards based on the [TI TRF7970A chip](http://www.ti.com/product/trf7970A), 
such as [TI's Evaluation Module](http://www.ti.com/tool/trf7970aevm) (EVM). 


Reading example:
```python
import yaml
from rfidgeek import PyRFIDGeek
config = yaml.load(open('config.yml', 'r'))
reader = PyRFIDGeek(config)
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

Writing example:
```python
import yaml
from rfidgeek import PyRFIDGeek

config = yaml.load(open('config.yml', 'r'))
rfid = PyRFIDGeek(config)
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

Installation for the websocket example:
* Install the websocket python package: `pip install websocket-client` 
