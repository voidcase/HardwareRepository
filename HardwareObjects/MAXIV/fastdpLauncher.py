#!/usr/bin/env python
# called this way
# fastdpLauncher.py -path /data/staff/biomax/staff/jie/2015_11_10/processed -mode after -datacollectionID 13 -residues 200 -anomalous False -cell "0,0,0,0,0,0"

import os
import sys
import time
import string
import urllib
import logging
import httplib
import logging
import tempfile
import subprocess, shlex

inputTemplate = """<?xml version="1.0"?>
<XSDataInputControlFastdp>
  <dataCollectionId>
    <value>{dataCollectionId}</value>
  </dataCollectionId>
  <processDirectory>
    <path>
      <value>{fastdpPath}</value>
    </path>
  </processDirectory>
{spacegroupFragment}
{cellFragment}
</XSDataInputControlFastdp>
"""

SCRIPT_TEMPLATE = """#!/usr/bin/env python

import os
import sys
import time
import socket
import traceback

sys.path.insert(0, "/mxn/groups/biomax/cmxsoft/edna-mx/kernel/src")

from EDVerbose import EDVerbose
from EDFactoryPluginStatic import EDFactoryPluginStatic

beamline = "$beamline"
proposal = "$proposal"
dataCollectionId = $dataCollectionId
fastdpDirectory = "$fastdpDirectory"
inputFile = "$inputFile"

pluginName = "EDPluginControlFastdpv1_0"
os.environ["EDNA_SITE"] = "MAXIV_BIOMAX"
os.environ["ISPyB_user"]=""
os.environ["ISPyB_pass"]=""

EDVerbose.screen("Executing EDNA plugin %s" % pluginName)
EDVerbose.screen("EDNA_SITE %s" % os.environ["EDNA_SITE"])

hostname = socket.gethostname()
dateString  = time.strftime("%Y%m%d", time.localtime(time.time()))
timeString = time.strftime("%H%M%S", time.localtime(time.time()))
#strPluginBaseDir = os.path.join("/tmp", beamline, dateString)
#if not os.path.exists(strPluginBaseDir):
#    os.makedirs(strPluginBaseDir, 0o755)

#baseName = "{0}_fastdp".format(timeString)
#baseDir = os.path.join(strPluginBaseDir, baseName)
baseName = "{hostname}_{date}-{time}".format(hostname=hostname,
                                             date=dateString,
                                             time=timeString)
baseDir = os.path.join(fastdpDirectory, baseName)
if not os.path.exists(baseDir):
    os.makedirs(baseDir, 0o755)
EDVerbose.screen("EDNA plugin working directory: %s" % baseDir)

#linkName = "{hostname}_{date}-{time}".format(hostname=hostname,
#                                             date=dateString,
#                                             time=timeString)
#os.symlink(baseDir, os.path.join(fastdpDirectory, linkName))

ednaLogName = "fastdp_{0}-{1}.log".format(dateString, timeString)
EDVerbose.setLogFileName(os.path.join(fastdpDirectory, ednaLogName))
EDVerbose.setVerboseOn()

edPlugin = EDFactoryPluginStatic.loadPlugin(pluginName)
edPlugin.setDataInput(open(inputFile).read())
#edPlugin.setBaseDirectory(strPluginBaseDir)
edPlugin.setBaseDirectory(fastdpDirectory)
edPlugin.setBaseName(baseName)

EDVerbose.screen("Start of execution of EDNA plugin %s" % pluginName)
os.chdir(baseDir)
edPlugin.executeSynchronous()

"""

HPC_HOST = "b-picard07-clu0-fe-0.maxiv.lu.se"


class fastdpLauncher:

    def __init__(self, path, mode, datacollectionID, residues=200, anomalous=False, cell="0,0,0,0,0,0", spacegroup=0):
        self.autoprocessingPath = path
        self.mode = mode
        self.dataCollectionId = datacollectionID
        self.nres = residues
        self.anomalous = anomalous
        self.cell = cell
        self.spacegroup = spacegroup
        self.log = logging.getLogger()
        self.log.setLevel(logging.DEBUG)
        self.xdsAppeared = False
        self.fastdpPath = os.path.join(self.autoprocessingPath, "fastdp")
        if not os.path.exists(self.fastdpPath):
            os.makedirs(self.fastdpPath, 0o755)
        self.xdsInputFile = os.path.join(self.autoprocessingPath, "XDS.INP")
        self.doAnomAndNonanom = True

    def parse_input_file(self):
        # the other parameters are not used right now
        if self.spacegroup is not None:
            spacegroupFragment = """  <spacegroup>
            <value>{0}</value>
            </spacegroup>""".format(self.spacegroup)
        else:
            spacegroupFragment = ""

        if self.cell is not None and self.cell!="0,0,0,0,0,0":
            cellFragment = """  <cell>
            <value>{0}</value>
            </cell>""".format(self.cell)
        else:
            cellFragment = ""


        self.inputXml = inputTemplate.format(dataCollectionId=self.dataCollectionId,
                                             cellFragment=cellFragment,
                                             spacegroupFragment=spacegroupFragment,
                                             fastdpPath=self.fastdpPath)

        # we now need a temp file in the data dir to write the data model to
        ednaInputFileName = "fastdp_input.xml"
        self.ednaInputFilePath = os.path.join(self.fastdpPath, ednaInputFileName)
        if os.path.exists(self.ednaInputFilePath):
            # Create unique file name
            ednaInputFile = tempfile.NamedTemporaryFile(suffix=".xml",
                                                        prefix="fastdp_input-",
                                                        dir=self.fastdpPath,
                                                        delete=False)
            self.ednaInputFilePath = os.path.join(self.fastdpPath, ednaInputFile.name)
            ednaInputFile.file.write(self.inputXml)
            ednaInputFile.close()
        else:
            open(self.ednaInputFilePath, "w").write(self.inputXml)
        os.chmod(self.ednaInputFilePath, 0o755)


        directories = self.autoprocessingPath.split(os.path.sep)
        try:
            beamline = directories[3]
            proposal = directories[4]
        except:
            beamline = "unknown"
            proposal = "unknown"

        #to do restrict fastdp only for academic users!?


        template = string.Template(SCRIPT_TEMPLATE)
        self.script = template.substitute(beamline=beamline,
                                     proposal=proposal,
                                     fastdpDirectory=self.fastdpPath,
                                     dataCollectionId=self.dataCollectionId,
                                     inputFile=self.ednaInputFilePath)

        # we also need some kind of script to run edna-plugin-launcher
        ednaScriptFileName = "fastdp_launcher.sh"
        self.ednaScriptFilePath = os.path.join(self.fastdpPath, ednaScriptFileName)
        if os.path.exists(self.ednaScriptFilePath):
            # Create unique file name
            ednaScriptFile = tempfile.NamedTemporaryFile(suffix=".sh",
                                                         prefix="fastdp_launcher-",
                                                         dir=self.fastdpPath,
                                                         delete=False)
            self.ednaScriptFilePath = os.path.join(self.fastdpPath, ednaScriptFile.name)
            ednaScriptFile.file.write(self.script)
            ednaScriptFile.close()
        else:
            open(self.ednaScriptFilePath, "w").write(self.script)
        os.chmod(self.ednaScriptFilePath, 0o755)

    def execute(self):

        cmd = "echo 'cd %s;source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh -F /etc/ssh/.ssh -o UserKnownHostsFile=/etc/ssh/.ssh/known_host -i /etc/ssh/id_rsa_biomax-service %s; source /mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_HPC.bash_profile" % (self.fastdpPath, self.ednaScriptFilePath, HPC_HOST)

        # for test
        #cmd = "echo 'cd %s;/mxn/groups/biomax/cmxsoft/edna-mx/scripts_maxiv/edna_sbatch.sh %s' | ssh %s" % (fastdpPath, ednaScriptFilePath, hpc_host)
        #print cmd
        logging.getLogger('HWR').info("Autoproc launcher: command gonna be launched: %s" % cmd)

        p = subprocess.Popen(cmd, shell=True) #, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        p.wait()

    def parse_and_execute(self):
        self.parse_input_file()
        self.execute()

if __name__ == "__main__":
    args = sys.argv[1:]

    if (len(args) % 2) != 0:
        logging.error("the argument list is not well formed (odd number of args/options)")
        sys.exit()

    # do the arg parsing by hand since neither getopt nor optparse support
    # single dash long options.
    options = dict()
    for x in range(0, len(args), 2):
        options[args[x]] = args[x + 1]

    autoprocessingPath = options["-path"]

    residues = float(options.get("-residues", 200))
    anomalous = options.get("-anomalous", False)
    spacegroup = options.get("-sg", None)
    cell = options.get("-cell", "0,0,0,0,0,0")
    dataCollectionId = options["-datacollectionID"]
    mode = options.get("-mode")

    autoProc = AutoProcLauncher(autoprocessingPath, mode, dataCollectionId, residues, anomalous, cell, spacegroup)
    autoProc.parse_and_execute()
