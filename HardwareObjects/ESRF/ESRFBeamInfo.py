import logging
from HardwareRepository import HardwareRepository
import BeamInfo

"""
XML example file
<object class="ESRF.ESRFBeamInfo">
  <defaultBeamDivergence></defaultBeamDivergence>
  <device role="camera" hwrid="/prosilica_md2"/>
  <device role="aperture" hwrid="/udiff_aperturemot"/>
  <!-- Positions and slits format: X Y -->
  <beam_position>322 243</beam_position>
  <beam_size_slits>0.04 0.04</beam_size_slits>
  <beam_divergence_vertical>6.5</beam_divergence_vertical>
  <beam_divergence_horizontal>104</beam_divergence_horizontal>
</object>
"""


class ESRFBeamInfo(BeamInfo.BeamInfo):
    def __init__(self, *args):
        BeamInfo.BeamInfo.__init__(self, *args)

    def init(self):
        self.chan_beam_size_microns = None
        self.chan_beam_shape_ellipse = None
        BeamInfo.BeamInfo.init(self)

        beam_size_slits = self.getProperty('beam_size_slits')
        if beam_size_slits:
            self.beam_size_slits = map(float, beam_size_slits.split())
        self.camera = self.getDeviceByRole("camera")

        beam_position = self.getProperty('beam_position')
        if beam_position:
            self.beam_position = tuple(map(float, beam_position.split()))
        else:
            self.beam_position = (self.camera.getWidth() / 2,
                                  self.camera.getHeight() / 2)

        self.flux = self.getObjectByRole("flux")

    def get_beam_position(self):
        return self.beam_position

    def set_beam_position(self, beam_x, beam_y):
        return

    def evaluate_beam_info(self, *args):
        BeamInfo.BeamInfo.evaluate_beam_info(self, *args)
        self.beam_info_dict["shape"] = "ellipse"
        return self.beam_info_dict

    def get_flux(self):
        return self.flux.getCurrentFlux()
