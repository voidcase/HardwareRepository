from HardwareRepository.BaseHardwareObjects import HardwareObject
from BeamCmds import (ControllerCommand, HWObjActuatorCommand)

class ID29BeamCmds(HardwareObject):
    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    def init(self):
        controller = self.getObjectByRole("controller")
        detcover = self.getObjectByRole("detcover")
        scintilator = self.getObjectByRole("scintilator")
        aperture = self.getObjectByRole("aperture")
        hutchtrigger = self.getObjectByRole("hutchtrigger")
        cryo = self.getObjectByRole("cryo")

        controller.detcover.set_in()
        self.centrebeam = ControllerCommand("Centre beam",
                                            controller.centrebeam)
        self.quick_realign = ControllerCommand("Quick realign",
                                              controller.quick_realign)
        self.anneal = ControllerCommand("Anneal",
                                        controller.anneal_procedure)

        self.detcover = HWObjActuatorCommand("Detector cover", detcover)
        self.scintilator = HWObjActuatorCommand("Scintilator", scintilator)
        self.aperture = HWObjActuatorCommand("Aperture", aperture)
        self.hutchtrigger = HWObjActuatorCommand("Hutchtrigger", hutchtrigger)
        self.cryo = HWObjActuatorCommand("Cryo", cryo)

    def getCommands(self):
        return [self.centrebeam, self.quick_realign, self.anneal,
                self.detcover, self.scintilator, self.aperture,
                self.hutchtrigger, self.cryo]
