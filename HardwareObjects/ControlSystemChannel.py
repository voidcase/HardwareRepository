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

class ControlSystemChannel(Device):
    def init(self):
        self._chan = self.getChannelObject("channel")
        self._chan.connectSignal("update", self.value_changed)
        self._name = self.username

    def getName(self):
        return self._name

    def getValue(self):
        return self._chan.getValue()

    def value_changed(self, value):
        self.emit("valueChanged", value) 

def test():
    import os
    import sys
    import gevent

    hwr_directory = os.environ["XML_FILES_PATH"]

    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    conn = hwr.getHardwareObject(sys.argv[1])

    print conn.getName()
    print conn.getValue()

    while True:
       gevent.wait(timeout=0.1)
       gevent.sleep(0.2)
       hwr.poll(1)
 
if __name__ == '__main__':
    test()
