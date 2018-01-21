from XRFSpectrum import *
import logging


class ID29XRFSpectrum(XRFSpectrum):
    def __init__(self, name):
        XRFSpectrum.__init__(self)

    def preset_mca(self, fname=None):
        self.mca_hwobj.set_roi(2, 15, channel=1)
        self.mca_hwobj.set_presets(erange=1, fname=fname)

    def choose_attenuation(self, ctime, fname=None):
        if not fname:
            fname = self.spectrumInfo["filename"]

        self.ctrl_hwobj.detcover.set_in()
        try:
            tt = self.ctrl_hwobj.find_max_attenuation(ctime=ctime, fname=fname)
            self.spectrumInfo["beamTransmission"] = tt
        except Exception as e:
            logging.getLogger('user_level_log').exception(str(e))
            raise e

    def _findAttenuation(self, ct):
        self.choose_attenuation(ct)
