#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name]
ALBAZoomMotorAutoBrightness

[Description]
Hardware Object is used to manipulate the zoom IOR and the
paired backlight intensity (slave IOR)

[Channels]
- None

[Commands]

[Emited signals]
- stateChanged
- predefinedPositionChanged

[Functions]
- None

[Included Hardware Objects]
- zoom
- blight

Example Hardware Object XML file :
==================================
<device class="ALBAZoomMotorAutoBrightness">
  <object role="zoom" hwrid="/zoom"></object>
  <object role="blight" hwrid="/blight"></object>
</device>
"""

from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging
import os
import PyTango

__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBAZoomMotorAutoBrightness(BaseHardwareObjects.Device):

    INIT, FAULT, READY, MOVING, ONLIMIT = range(5)

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)

    def init(self):
        logging.getLogger("HWR").debug("Initializing zoom motor autobrightness IOR")

        self.zoom = self.getObjectByRole('zoom')
        self.blight = self.getObjectByRole('blight')
 
        self.zoom.positionChannel.connectSignal("update", self.positionChanged)
        self.zoom.stateChannel.connectSignal("update", self.stateChanged)


    def getPredefinedPositionsList(self):
        retlist = self.zoom.getPredefinedPositionsList()
        logging.getLogger("HWR").debug("Zoom positions list: %s" % repr(retlist))
        return retlist
        

    def moveToPosition(self, posno):
        #no = posno.split()[0]
        #logging.getLogger("HWR").debug("Moving to position %s" % no)

        #self.blight.moveToPosition(posno)
        self.zoom.moveToPosition(posno)
        state = self.zoom.getState()
        #state = self.positionChannel.setValue(int(no))

    def motorIsMoving(self):
        return self.zoom.motorIsMoving()

#        if str(self.getState()) == "MOVING":
#             return True
#        else:
#             return False

    def getLimits(self):
        #return (1,12) 
        return self.zoom.getLimits()

    def getState(self):
#        state = self.stateChannel.getValue()
#        curr_pos = self.getPosition()
#        if state == PyTango.DevState.ON:
#             return ALBAZoomMotor.READY
#        elif state == PyTango.DevState.MOVING or state == PyTango.DevState.RUNNING:
#             return ALBAZoomMotor.MOVING
#        elif curr_pos in self.getLimits():
#             return ALBAZoomMotor.ONLIMIT
#        else:
#             return ALBAZoomMotor.FAULT
#        return state
        return self.zoom.getState()
   
    def getPosition(self):
#        return self.positionChannel.getValue()
        return self.zoom.getPosition()
   
    def getCurrentPositionName(self):
#        n = int(self.positionChannel.getValue())
#        value = "%s z%s" % (n, n)
#        logging.getLogger("HWR").debug("getCurrentPositionName: %s" % repr(value))
#        return value
         return self.zoom.getCurrentPositionName()
    
    def stateChanged(self, state):
        logging.getLogger("HWR").debug("stateChanged emitted: %s" % state)
        self.emit('stateChanged', (self.getState(), ))

    def positionChanged(self, currentposition):
        currentposition = self.getCurrentPositionName()
        logging.getLogger("HWR").debug("predefinedPositionChanged emitted: %s" % currentposition)
        # Update light brightness step-by-step
        posno = currentposition.split()[0]
        logging.getLogger("HWR").debug("Moving brightness to: %s" % posno)

        self.blight.moveToPosition(posno)
        
        
        self.emit('predefinedPositionChanged', (currentposition, 0))

    def isReady(self):
        state = self.getState()
        return state == ALBAZoomMotorAutoBrightness.READY


def test():
  hwr_directory = os.environ["XML_FILES_PATH"]

  print "Loading hardware repository from ", os.path.abspath(hwr_directory)
  hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
  hwr.connect()

  zoom = hwr.getHardwareObject("/zoom-auto-brightness")

  print type(zoom.getState() )

  print "     Zoom position is : ",zoom.getPosition()
  print "Zoom position name is : ",zoom.getCurrentPositionName()
  print "               Moving : ",zoom.motorIsMoving()
  print "                State : ",zoom.getState()
  print "            Positions : ",zoom.getPredefinedPositionsList()

if __name__ == '__main__':
   test()
