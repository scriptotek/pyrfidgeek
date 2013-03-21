**PyRFIDGeek** is a python package for serial communication with [RFIDGeek](http://rfidgeek.com/) boards 
(tested with RFIDUARTUSB7970) and possibly other boards based on the [TI TRF7970A chip](http://www.ti.com/product/trf7970A), 
such as [TI's Evaluation Module](http://www.ti.com/tool/trf7970aevm) (EVM). 
The package includes methods for working with cards following the Danish RFID data model for libraries.


Example:
```
import yaml
from rfidgeek import PyRFIDGeek
config = yaml.load(open('config.yml', 'r'))
reader = PyRFIDGeek(config)
for uid in reader.inventory(single_slot=False):
    item = reader.read_tag_danish_model(uid)
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
