"""
[Name] ControlSystemChannel

[Description]
The ControlSystemChannel hardware object offers a standard interface to a 
single channel object in the HardwareRepository system. It is a way to expose
a value (in any of the supported control systems (Tango, Tine, Sardana, Epics..)
for a simple use by the final application user interface.

[Commands]
getValue()
   return:
       current value of the channel

getName()
   return:
       name configured for the channel

[Emited signals]
valueChanged
   pars: value

   value :  updated value of the channel  

"""
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device

class ControlSystemChannelList(Device):
    def init(self):
        self._name = self.username
        self._chans = {}

        for name in self.getChannelNamesList():
            _chan = self.getChannelObject(name)
            _chan.connectSignal("update", \
                lambda value, name=name, this=self: \
                   ControlSystemChannelList.value_changed(this,name, value))
            self._chans[name] = _chan

    def getName(self):
        return self._name

    def getValues(self):
        ret = {}
        for name in self._chans:
            ret[name] = self._chans[name].getValue()
        return ret

    def value_changed(self, name, value):
        self.emit("value_changed", name, value) 

def test():
    import os
    import sys
    import gevent

    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    conn = hwr.getHardwareObject(sys.argv[1])
    # conn.connect("temperature_changed", print_temperature)

    print conn.getValues()
    # print conn.getValue()
 
if __name__ == '__main__':
    test()
