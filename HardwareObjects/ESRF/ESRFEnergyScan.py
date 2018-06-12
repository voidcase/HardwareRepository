from HardwareRepository.BaseHardwareObjects import HardwareObject
from AbstractEnergyScan import *
from gevent.event import AsyncResult
import logging
import time
import os
import os.path
import shutil
import httplib
import math
import PyChooch
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


class FixedEnergy:

    @task
    def get_energy(self):
        return self._tunable_bl.energy_obj.getPosition()


class TunableEnergy:

    @task
    def get_energy(self):
        return self._tunable_bl.energy_obj.getCurrentEnergy()

    @task
    def move_energy(self, energy):
        return self._tunable_bl.energy_obj.startMoveEnergy(energy, wait=True)


class GetStaticParameters:
    def __init__(self, config_file, element, edge):
        self.element = element
        self.edge = edge
        self.STATICPARS_DICT = {}
        self.STATICPARS_DICT = self._readParamsFromFile(config_file)

    def _readParamsFromFile(self, config_file):
        with open(config_file, 'r') as f:
            array = []
            for line in f:
                if not line.startswith('#') and self.element in line:
                    array = line.split()
                    break

            try:
                static_pars = {}
                static_pars['atomic_nb'] = int(array[0])
                static_pars['eroi_min'] = float(array[11])/1000.
                static_pars['eroi_max'] = float(array[12])/1000.

                if 'K' in self.edge:
                    th_energy = float(array[3])/1000.
                else:
                    if '1' in self.edge:
                        # L1
                        th_energy = float(array[6])/1000.
                    elif '2' in self.edge:
                        # L2
                        th_energy = float(array[7])/1000.
                    else:
                        # L or L3
                        th_energy = float(array[8])/1000.

                # all the values are in keV
                static_pars['edgeEnergy'] = th_energy
                static_pars['startEnergy'] = th_energy - 0.05
                static_pars['endEnergy'] = th_energy + 0.05
                static_pars['findattEnergy'] = th_energy + 0.03
                static_pars['remoteEnergy'] = th_energy + 1
                return static_pars
            except Exception as e:
                print e
                return {}


class ESRFEnergyScan(AbstractEnergyScan, HardwareObject):
    def __init__(self, name, tunable_bl):
        AbstractEnergyScan.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = tunable_bl

    def execute_command(self, command_name, *args, **kwargs):
        wait = kwargs.get('wait', True)
        cmd_obj = self.getCommandObject(command_name)
        return cmd_obj(*args, wait=wait)

    def init(self):
        self.energy_obj = self.getObjectByRole('energy')
        self.safety_shutter = self.getObjectByRole('safety_shutter')
        self.beamsize = self.getObjectByRole('beamsize')
        self.transmission = self.getObjectByRole('transmission')
        self.ready_event = gevent.event.Event()
        self.dbConnection = self.getObjectByRole('dbserver')
        if self.dbConnection is None:
            logging.getLogger('HWR').warning("EnergyScan: you should specify the database hardware object")
        self.scanInfo = None
        self._tunable_bl.energy_obj = self.energy_obj

    def isConnected(self):
        return True

    def get_static_parameters(self, config_file, element, edge):
        pars = GetStaticParameters(config_file, element, edge).STATICPARS_DICT

        offset_keV = self.getProperty('offset_keV')
        pars['startEnergy'] += offset_keV
        pars['endEnergy'] += offset_keV
        pars['element'] = element

        return pars

    def open_safety_shutter(self, timeout=None):
        self.safety_shutter.openShutter()
        with gevent.Timeout(timeout, RuntimeError("Timeout waiting for safety shutter to open")):
            while self.safety_shutter.getShutterState() == 'closed':
                time.sleep(0.1)

    def close_safety_shutter(self, timeout=None):
        self.safety_shutter.closeShutter()
        while self.safety_shutter.getShutterState() == 'opened':
            time.sleep(0.1)

    def escan_prepare(self):

        if self.beamsize:
            bsX = self.beamsize.getCurrentPositionName()
            self.energy_scan_parameters['beamSizeHorizontal'] = bsX
            self.energy_scan_parameters['beamSizeVertical'] = bsX

    def escan_postscan(self):
        self.execute_command('cleanScan')

    def escan_cleanup(self):
        self.close_fast_shutter()
        self.close_safety_shutter()
        try:
            self.execute_command('cleanScan')
        except Exception:
            pass
        self.emit('energyScanFailed', ())
        self.ready_event.set()

    def close_fast_shutter(self):
        self.execute_command('close_fast_shutter')

    def open_fast_shutter(self):
        self.execute_command('open_fast_shutter')

    def move_energy(self, energy):
        try:
            self._tunable_bl.energy_obj.move_energy(energy)
        except:
            self.emit('energyScanFailed', ())
            raise RuntimeError("Cannot move energy")

    # Elements commands
    def getElements(self):
        elements = []
        try:
            for el in self['elements']:
                elements.append({'symbol': el.symbol, 'energy': el.energy})
        except IndexError:
            pass

        return elements

    def storeEnergyScan(self):
        if self.dbConnection is None:
            return
        try:
            session_id = int(self.energy_scan_parameters['sessionId'])
        except Exception:
            return

        # remove unnecessary for ISPyB fields:
        self.energy_scan_parameters.pop('prefix')
        self.energy_scan_parameters.pop('eroi_min')
        self.energy_scan_parameters.pop('eroi_max')
        self.energy_scan_parameters.pop('findattEnergy')
        self.energy_scan_parameters.pop('edge')
        self.energy_scan_parameters.pop('directory')
        self.energy_scan_parameters.pop('atomic_nb')

        gevent.spawn(StoreEnergyScanThread, self.dbConnection,
                     self.energy_scan_parameters)

    def doChooch(self, elt, edge, directory, archive_directory, prefix):
        self.energy_scan_parameters['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")

        raw_data_file = os.path.join(directory, 'data.raw')

        symbol = "_".join((elt, edge))
        archive_prefix = "_".join((prefix, symbol))
        raw_scan_file = os.path.join(directory, (archive_prefix + '.raw'))
        efs_scan_file = raw_scan_file.replace('.raw', '.efs')
        raw_arch_file = os.path.join(archive_directory,
                                        (archive_prefix + '1' + '.raw'))
        i = 0
        while os.path.isfile(raw_arch_file):
            i += 1
            raw_arch_file = os.path.join(archive_directory,
                                            (archive_prefix + str(i) + '.raw'))

        if not os.path.exists(archive_directory):
            os.makedirs(archive_directory)
        try:
            f = open(raw_scan_file, 'w')
        except IOError:
            self.storeEnergyScan()
            self.emit('energyScanFailed', ())
            return
        else:
            scan_data = []
            try:
                with open(raw_data_file, 'r') as raw_file:
                    for line in raw_file.readlines()[2:]:
                        try:
                            (x, y) = line.split('\t')
                        except:
                            (x, y) = line.split()
                        x = float(x.strip())
                        y = float(y.strip())
                        scan_data.append((x, y))
                        f.write("%f,%f\r\n" % (x, y))
                f.close()
            except IOError as e:
                self.storeEnergyScan()
                self.emit('energyScanFailed', ())
                return

        shutil.copy2(raw_scan_file, raw_arch_file)
        self.energy_scan_parameters['scanFileFullPath'] = raw_arch_file

        result = PyChooch.calc(scan_data, elt, edge, efs_scan_file)
        # PyChooch occasionally returns an error and the result
        # the sleep command assures that we get the result
        time.sleep(1)
        print result[0]
        pk = result[0]/1000.
        fppPeak = result[1]
        fpPeak = result[2]
        ip = result[3]/1000.
        fppInfl = result[4]
        fpInfl = result[5]
        chooch_graph_data = result[6]

        rm = pk+0.03

        comm = ""
        th_edge = float(self.energy_scan_parameters['edgeEnergy'])

        logging.getLogger('HWR').info("Chooch results: pk = %f, ip = %f, rm = %f, Theoretical edge: %f" % (pk, ip, rm, th_edge))

        # +- shift from the theoretical edge [eV]
        edge_shift = 10
        calc_shift = (th_edge - ip) * 1000
        if math.fabs(calc_shift) > edge_shift:
            rm = th_edge + 0.03
            comm = "%s" % "below" if (calc_shift) > edge_shift else "above"
            comm = "Calculated peak (%f) is more than %d eV %s the theoretical value (%f)." % (pk, edge_shift, comm, th_edge)

            logging.getLogger('user_level_log').warning("EnergyScan: %s Check your scan and choose the energies manually" % comm)
            pk = 0
            ip = 0

        efs_arch_file = raw_arch_file.replace('.raw', '.efs')
        if os.path.isfile(efs_scan_file):
            shutil.copy2(efs_scan_file, efs_arch_file)
        else:
            self.storeEnergyScan()
            self.emit('energyScanFailed', ())
            return

        self.energy_scan_parameters['filename'] = raw_arch_file.split('/')[-1]
        self.energy_scan_parameters['peakEnergy'] = pk
        self.energy_scan_parameters['inflectionEnergy'] = ip
        self.energy_scan_parameters['remoteEnergy'] = rm
        self.energy_scan_parameters['peakFPrime'] = fpPeak
        self.energy_scan_parameters['peakFDoublePrime'] = fppPeak
        self.energy_scan_parameters['inflectionFPrime'] = fpInfl
        self.energy_scan_parameters['inflectionFDoublePrime'] = fppInfl
        self.energy_scan_parameters['comments'] = comm

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        chooch_graph_x = [x/1000.0 for x in chooch_graph_x]

        logging.getLogger('HWR').info("Saving png")
        # prepare to save png files
        title = "%10s  %6s  %6s\n%10s  %6.2f  %6.2f\n%10s  %6.2f  %6.2f" % ("energy", "f'", "f''", pk, fpPeak, fppPeak, ip, fpInfl, fppInfl)
        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (efs_scan_file, title))
        ax.grid(True)
        ax.plot(*(zip(*scan_data)), **{'color': 'black'})
        ax.set_xlabel("Energy")
        ax.set_ylabel("MCA counts")
        ax2 = fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color='blue'))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color='red'))
        canvas = FigureCanvasAgg(fig)

        png_scan_file = raw_scan_file.replace('.raw', '.png')
        png_arch_file = raw_arch_file.replace('.raw', '.png')
        self.energy_scan_parameters['jpegChoochFileFullPath'] = str(png_arch_file)
        try:
            logging.getLogger('HWR').info("Rendering energy scan and Chooch graphs to PNG file : %s", png_scan_file)
            canvas.print_figure(png_scan_file, dpi=80)
        except:
            logging.getLogger('HWR').exception("could not print figure")
        try:
            logging.getLogger('HWR').info("Saving energy scan to archive directory for ISPyB : %s", png_arch_file)
            canvas.print_figure(png_arch_file, dpi=80)
        except:
            logging.getLogger('HWR').exception("could not save figure")

        self.storeEnergyScan()

        self.emit('chooch_finished', (pk, fppPeak, fpPeak,
                                      ip, fppInfl, fpInfl, rm,
                                      chooch_graph_x, chooch_graph_y1,
                                      chooch_graph_y2, title))
        return pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title


def StoreEnergyScanThread(db_conn, scan_info):
    scan_info = dict(scan_info)
    blsample_id = scan_info['blSampleId']
    scan_info.pop('blSampleId')

    try:
        db_status = db_conn.storeEnergyScan(scan_info)
        if blsample_id is not None:
            try:
                escan_id = int(db_status['energyScanId'])
            except (NameError, KeyError):
                pass
            else:
                asso = {'blSampleId': blsample_id, 'energyScanId': escan_id}
                db_conn.associateBLSampleAndEnergyScan(asso)
    except Exception as e:
        print e
