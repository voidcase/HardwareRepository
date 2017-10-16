
from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Device

class ALBAEnergy(Device):

    def __init__(self,*args):
        Device.__init__(self,*args)
        self.energy_position = None
        self.wavelength_position = None

    def init(self):
        self.energy_hwobj = self.getObjectByRole("energy")
        self.wavelength_hwobj = self.getObjectByRole("wavelength")

        self.energy_hwobj.connect("positionChanged", self.energy_position_changed)
        self.wavelength_hwobj.connect("positionChanged", self.wavelength_position_changed)

    def isReady(self):
        return True
 
    def can_move_energy(self):
        return True

    def get_energy(self):
        return self.energy_position

    def update_values(self):
        self.energy_hwobj.update_values()

    def energy_position_changed(self, value):
        self.energy_position = value
        if None not in [self.energy_position, self.wavelength_position]: 
            self.emit('energyChanged', self.energy_position, self.wavelength_position)

    def wavelength_position_changed(self, value):
        self.wavelength_position = value
        if None not in [self.energy_position, self.wavelength_position]: 
            self.emit('energyChanged', self.energy_position, self.wavelength_position)

    def move_energy(self, value):
        self.energy_hwobj.move(value)

    def move_wavelength(self, value):
        self.wavelength_hwobj.move(value)

    def get_energy_limits(self):
        return self.energy_hwobj.getLimits()
 
    def get_wavelength_limits(self):
        return self.wavelength_hwobj.getLimits()
 
def test():
    import os
    hwr_directory = os.environ["XML_FILES_PATH"]
    hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
    hwr.connect()

    energy = hwr.getHardwareObject("/energy")
    print "Energy is: ",energy.get_energy()
    print "Energy limits are: ",energy.get_energy_limits()
    print "Wavelength limits are: ",energy.get_wavelength_limits()

if __name__ == '__main__':
    test()
