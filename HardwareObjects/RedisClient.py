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
Redis hardware object acts as a client to Redis DB and saves
graphical objects and queue after closing MXCuBE.
Install redis: sudo pip install redis
Start server on local pc: redis-server &
It is recommended to start redis with mxcube

example xml:

<object class="RedisClient">
   <object href="/beamline-setup" role="beamline_setup"/>
   <object href="/queue-model" role="queue_model"/>
</object>
"""

import redis
import gevent
import logging
import jsonpickle

from HardwareRepository.BaseHardwareObjects import HardwareObject


__version__ = "2.3."
__category__ = "General"


class RedisClient(HardwareObject):

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.host = None
        self.port = None
        self.active = None
        self.proposal_id = None
        self.beamline_name = None
        self.redis_client = None
        
        self.bl_setup_hwobj = None
        self.queue_model_hwobj = None

    def init(self):
        self.host = self.getProperty("host")
        if self.host is None:
            self.host = "localhost"

        self.port = self.getProperty("port")
        if self.port is None:
            self.port = 6379

        self.redis_client = redis.StrictRedis(host=self.host, port=self.port, db=0)

        try:
            if self.redis_client.ping():
                self.active = True
        except:
            self.active = False

        if self.active:
            logging.getLogger("HWR").info(\
                "RedisClient: listening to connections on %s:%d" % \
                (self.host, self.port))
        else:
            logging.getLogger("HWR").error(\
                "RedisClient: Redis server %s:%d is not available" % \
                (self.host, self.port))

        self.queue_model_hwobj = self.getObjectByRole("queue_model")
        self.bl_setup_hwobj = self.getObjectByRole("beamline_setup")

        self.connect(self.bl_setup_hwobj.flux_hwobj,
                     'fluxChanged',
                     self.flux_changed)

        self.proposal_id = self.bl_setup_hwobj.session_hwobj.get_proposal()
        self.beamline_name = self.bl_setup_hwobj.session_hwobj.beamline_name

        if self.active:
            self.init_beamline_setup()

    def save_queue(self):
        """Saves queue in RedisDB"""
        if self.active:
            gevent.spawn(self.save_queue_task)

    def save_queue_task(self):
        """Queue saving tasks"""
        selected_model, queue_list = self.queue_model_hwobj.get_queue_as_json_list()
        self.redis_client.set("mxcube:%s:%s:queue_model" % \
                              (self.proposal_id, self.beamline_name),
                               selected_model)
        self.redis_client.set("mxcube:%s:%s:queue_current" % \
                              (self.proposal_id, self.beamline_name),
                               queue_list)
        logging.getLogger("HWR").debug("RedisClient: Current queue saved")

    def load_queue(self):
        """Loads queue from redis DB"""
        if self.active:
            self.active = False
            selected_model = None

            selected_model = self.redis_client.get(\
                 "mxcube:%s:%s:queue_model" % \
                 (self.proposal_id, self.beamline_name))
            serialized_queue = self.redis_client.get(\
                 "mxcube:%s:%s:queue_current" % \
                 (self.proposal_id, self.beamline_name))
            if selected_model is not None:
                self.queue_model_hwobj.select_model(selected_model)
                self.queue_model_hwobj.load_queue_from_json_list(\
                     eval(serialized_queue),
                     snapshot=self.bl_setup_hwobj.shape_history_hwobj.get_scene_snapshot())

            self.active = True
            logging.getLogger("HWR").debug("RedisClient: Queue loaded")
            return selected_model

    def save_graphics(self):
        """Saves graphics objects in RedisDB"""
        if self.active:
            logging.getLogger("HWR").debug(\
                    "RedisClient: Graphics saved at " + \
                    "mxcube:%s:%s:graphics" % \
                    (self.proposal_id, self.beamline_name))
            graphic_objects = self.bl_setup_hwobj.shape_history_hwobj.dump_shapes()
            self.redis_client.set("mxcube:%s:%s:graphics" % \
                                  (self.proposal_id, self.beamline_name),
                                  jsonpickle.encode(graphic_objects))

    def load_graphics(self):
        """Loads graphics from RedisDB"""
        if self.active:
            try:
                graphics_objects = self.redis_client.get("mxcube:%s:%s:graphics" % \
                      (self.proposal_id, self.beamline_name))
                self.bl_setup_hwobj.shape_history_hwobj.load_shapes(\
                      jsonpickle.decode(graphics_objects))
                logging.getLogger("HWR").debug("RedisClient: Graphics loaded")
            except:
                pass

    def save_queue_history_item(self, item):
        """Saves queue history in redisDB"""
        if self.active:
            self.redis_client.lpush("mxcube:%s:%s:queue_history" % \
                                    (self.proposal_id, self.beamline_name),
                                    str(item))
            logging.getLogger("HWR").debug("RedisClient: History queue saved")

    def load_queue_history(self):
        """Loads queue history from redisDB"""
        result = []
        if self.active:
            try:
                items = self.redis_client.lrange("mxcube:%s:%s:queue_history" % \
                                                 (self.proposal_id, self.beamline_name),
                                                 0, -1)
                for item in items:
                    result.append(eval(item))
            except:
                pass
        return result

    def clear_db(self):
        """Cleans redisDB"""
        if self.active:
            self.redis_client.flushdb()

    def flux_changed(self, value, beam_info, transmission):
        self.save_beamline_setup_item("flux", (value, beam_info, transmission))

    def init_beamline_setup(self):
        try:
            self.active = False
            flux_value = self.redis_client.get("mxcube:%s:%s:flux" % \
                                         (self.proposal_id, self.beamline_name))
            
            print flux_value
            self.active = True
        except Exception as ex:
            logging.getLogger("HWR").debug(\
                 "Redis: Exception in reading beamline setup: %s" % str(ex))
        

    def save_beamline_setup_item(self, key, value):
        if self.active:
            if key == "flux":
                logging.getLogger("HWR").debug("RedisClient: Flux value saved")
                self.redis_client.set("mxcube:%s:%s:flux" %\
                                      (self.proposal_id, self.beamline_name),
                                       value[0])
     
