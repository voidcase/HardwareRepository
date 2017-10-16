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
ALBACalibration

[Description]
HwObj used to grab the zoom/pixel size calibration from
PySignal simulator (TangoDS).


Example Hardware Object XML file :
==================================
<device class="ALBACalibration">
  <username>Calibration</username>
  <taurusname>bl13/ct/variables</taurusname>
  <channel type="sardana" name="calibx">OAV_PIXELSIZE_X</channel>
  <channel type="sardana" name="caliby">OAV_PIXELSIZE_Y</channel>
  <interval>200</interval>
  <threshold>0.001</threshold>
</device>
"""

from HardwareRepository import HardwareRepository
from HardwareRepository import BaseHardwareObjects
import logging
import os

__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"

class ALBACalibration(BaseHardwareObjects.Device):

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)

    def init(self):

        self.calibx = self.getChannelObject("calibx")
        self.caliby = self.getChannelObject("caliby")

        if self.calibx is not None and self.caliby is not None:
            logging.getLogger().info("Connected to pixel size calibration channels")

    def getCalibration(self):
        calibx = self.calibx.getValue()
        caliby = self.caliby.getValue()
        logging.getLogger().debug("Returning calibration: x=%s, y=%s" % (calibx, caliby))
        return [calibx , caliby]

def test():
  hwr_directory = os.environ["XML_FILES_PATH"]

  print "Loading hardware repository from ", os.path.abspath(hwr_directory)
  hwr = HardwareRepository.HardwareRepository(os.path.abspath(hwr_directory))
  hwr.connect()

  calib = hwr.getHardwareObject("/calibration")
  print "Calibration is: ",calib.getCalibration()

if __name__ == '__main__':
   test()
