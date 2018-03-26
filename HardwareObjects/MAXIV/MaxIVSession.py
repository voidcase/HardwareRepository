"""
MAXIV Session hardware object.

Adapting from original Session.py to adapt the names of data directories
"""
import os
import time
import socket
import logging
try:
    from sdm import storage, Visitor
except:
    raise Exception('Cannot import SDM library.')

from Session import Session
import queue_model_objects_v1 as queue_model_objects


class MaxIVSession(Session):
    def __init__(self, name):
        Session.__init__(self, name)

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        self.default_precision = "04"
        self.login = ''
        self.is_commissioning = False
        self.synchrotron_name = self.getProperty('synchrotron_name')
        self.endstation_name = self.getProperty('endstation_name').lower()
        self.suffix = self["file_info"].getProperty('file_suffix')
        self.base_directory = self["file_info"].getProperty('base_directory')

        self.base_process_directory = self["file_info"].\
            getProperty('processed_data_base_directory')

        self.raw_data_folder_name = self["file_info"].\
            getProperty('raw_data_folder_name')

        self.processed_data_folder_name = self["file_info"].\
            getProperty('processed_data_folder_name')

        try:
            self.in_house_users = self.getProperty("inhouse_users").split(',')
        except:
            self.in_house_users = []

        try:
            domain = socket.getfqdn().split('.')
            self.email_extension = '.'.join((domain[-2], domain[-1]))
        except (TypeError, IndexError):
            pass

        archive_base_directory = self['file_info'].getProperty('archive_base_directory')
        if archive_base_directory:
            queue_model_objects.PathTemplate.set_archive_path(archive_base_directory,
                                                              self['file_info'].getProperty('archive_folder'))

        queue_model_objects.PathTemplate.set_path_template_style(self.synchrotron_name)
        queue_model_objects.PathTemplate.set_data_base_path(self.base_directory)

        self.commissioning_fake_proposal = {'Laboratory': {'address': None,
                                                           'city': 'Lund',
                                                           'laboratoryId': 312171,
                                                           'name': 'Lund University'},
                                            'Person': {'familyName': 'Commissioning',
                                                       'givenName': 'Commi',
                                                       'laboratoryId': 312171,
                                                       'login': 'staff',
                                                       'personId': 0},
                                            'Proposal': {'code': 'MX',
                                                         'number': time.strftime("%Y"),
                                                         'proposalId': '0',
                                                         'timeStamp': time.strftime("%Y%m%d"),
                                                         'title': 'Commissioning Proposal',
                                                         'type': 'MX'},
                                            'Session': [{'is_inhouse': True,
                                                         'beamlineName': 'BioMAX',
                                                         'comments': 'Fake session for commissioning',
                                                         'endDate': '2027-12-31 23:59:59',
                                                         'nbShifts': 100,
                                                         'proposalId': '0',
                                                         'scheduled': 0,
                                                         'sessionId': 0,
                                                         'startDate': '2016-01-01 00:00:00'}
                                                        ]
                                            }

    def set_in_commissioning(self, proposal_info):
        self.proposal_code = proposal_info['Proposal']['code']
        self.proposal_number = proposal_info['Proposal']['number']
        self.is_commissioning = True

    def get_proposal(self):
        """
        :returns: The proposal, 'local-user' if no proposal is
                  available
        :rtype: str
        """
        proposal = 'local-user'

        if self.proposal_code and self.proposal_number:
            if self.proposal_code == 'ifx':
                self.proposal_code = 'fx'

            proposal = str(self.proposal_number)

        return proposal

    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """
        if self.session_start_date:
            start_time = self.session_start_date.split(' ')[0].replace('-', '')
        else:
            start_time = time.strftime("%Y%m%d")

        if not self.is_commissioning:
            # /data/visitors/biomax/prop/visit/
            # /data/(user-type)/(beamline)/(proposal)/(visit)/raw
            directory = os.path.join(self.base_directory,
                                     self.get_user_category(self.login),
                                     self.beamline_name.lower(),
                                     self.get_proposal(),
                                     start_time)
        else:
            # /data/staff/biomax/commissioning/date
            directory = os.path.join(self.base_directory,
                                    'staff',
                                    self.beamline_name.lower(),
                                    'commissioning',
                                    time.strftime("%Y%m%d"))

        logging.getLogger("HWR").info("[MAX IV Session] Data directory for proposal %s: %s" % (self.get_proposal(), directory))

        return directory

    def prepare_directories(self, proposal_info):
        self.login = proposal_info['Person']['login']
        start_time = proposal_info.get('Session')[0].get('startDate')
        
        logging.getLogger("HWR").info("[MAX IV Session] Preparing Data directory for proposal %s" % proposal_info)
        if start_time:
            start_date = start_time.split(' ')[0].replace('-', '')
        else:
            start_date = time.strftime("%Y%m%d")

        self.set_session_start_date(start_date)

        # this checks that the beamline data path has been properly created
        # e.g. /data/visitors/biomax
        try:
             self.storage = storage.Storage(self.get_user_category(self.login), self.endstation_name)
        except Exception as ex:
            print ex
            # this creates the path for the data and ensures proper permissions.
            # e.g. /data/visitors/biomax/<proposal>/<visit>/{raw, process}
        if self.is_commissioning:
            group = self.beamline_name.lower()
        else:
            group = self.storage.get_proposal_group(self.proposal_number)
        
        try:
            self.storage.create_path(self.proposal_number,
                                      group,
                                      self.get_session_start_date())

            proposal_path = '{0}/{1}'.format(self.storage.beamline_path, self.proposal_number)
            logging.getLogger("HWR").info("[MAX IV Session] SDM Data directory created: %s" % proposal_path)
        except Exception as ex:
            msg = "[MAX IV Session] SDM Data directory creation failed. %s" % ex
            logging.getLogger("HWR").error(msg)
            raise Exception(msg)

    def is_inhouse(self, user, code=None):
        """
        Determines if a given user is considered to be inhouse.
        :param login: username
        :type login: str
        :returns: True if the user is inhouse, otherwise False.
        :rtype: bool
        """
        if user in self.in_house_users:
            return True
        else:
            return False

    def get_user_category(self, user):
        # 'staff','visitors', 'proprietary'
        # missing industrial users
        if self.is_inhouse(user) or user == 'staff':
            user_category = 'staff'
        else:
            user_category = 'visitors'
        return user_category

    def clear_session(self):
        self.session_id = None
        self.proposal_code = None
        self.proposal_number = None

        self.login = ''        
        self.is_commissioning = False
