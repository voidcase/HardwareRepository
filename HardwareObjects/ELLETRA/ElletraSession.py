"""
Session hardware object.

Contains information regarding the current session and methods to
access and manipulate this information.
"""
import os
import time
import socket
import Session

import queue_model_objects_v1 as queue_model_objects

class ElletraSession(Session.Session):
    def __init__(self, name):
        Session.Session.__init__(self, name)


    def get_base_data_directory(self):
        """
        Returns the base data directory taking the 'contextual'
        information into account, such as if the current user
        is inhouse.

        :returns: The base data path.
        :rtype: str
        """

        return self.base_directory

    def get_base_image_directory(self):
        """
        :returns: The base path for images.
        :rtype: str
        """
        return self.get_base_data_directory()

    def get_base_process_directory(self):
        """
        :returns: The base path for procesed data.
        :rtype: str
        """
        return os.path.join(self.get_base_data_directory(),
                            self.processed_data_folder_name)

    def get_image_directory(self, sub_dir=None):
        """
        Returns the full path to images, using the name of each of
        data_nodes parents as sub directories.

        :param data_node: The data node to get additional
                          information from, (which will be added
                          to the path).
        :type data_node: TaskNode

        :returns: The full path to images.
        :rtype: str
        """
        directory = self.get_base_image_directory()

        return directory

    def get_process_directory(self, sub_dir=None):
        """
        Returns the full path to processed data, using the name of
        each of data_nodes parents as sub directories.

        :param data_node: The data node to get additional
                          information from, (which will be added
                          to the path).
        :type data_node: TaskNode

        :returns: The full path to images.
        """
        directory = self.get_base_process_directory()

        return directory

    def get_default_prefix(self, sample_data_node = None, generic_name = False):
        """
        Returns the default prefix, using sample data such as the
        acronym as parts in the prefix.

        :param sample_data_node: The data node to get additional
                                 information from, (which will be
                                 added to the prefix).
        :type sample_data_node: Sample


        :returns: The default prefix.
        :rtype: str
        """

        if sample_data_node:
            prefix = "%s" % sample_data_node.name
        elif generic_name:
            prefix = '<name>'

        return prefix

    def get_default_subdir(self, sample_data):
        return ""

    def expand_variables(self, pt, extra_vars):
        if '{' in pt.directory:
            pt.directory = pt.directory.\
                format(sample_name = extra_vars.get("sample_name", ""),
                       proposal_id = extra_vars.get("proposal_id", "-1"),
                       run_number = pt.run_number)
