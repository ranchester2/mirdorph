# Copyright 2021 Raidro Manchester
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Heavily based on Giara code

import os
import json
import logging
import copy
from pathlib import Path

class ConfManager:
    """
    The ConfManager is a system that helps manage the configuration
    of the application.

    It is recommended to ever only have one instane, and add it to 
    your application class
    """

    BASE_SCHEMA = {
        'added_channels': [
        ]
    }

    def __init__(self, path=None):
        """
        Create a ConfManager

        param:
            path: (optional) override the default path
        """
        if path is None:
            self.path = Path(os.environ["XDG_CONFIG_HOME"] + "/" + "mirdorph.conf.json")
        else:
            self.path = path
            
        if self.path.is_file():
            try:
                with open(str(self.path)) as fd:
                    self._conf = json.loads(fd.read())
                # verify thatfor k in ConfManager.BASE_SCHEMA:
                for k in ConfManager.BASE_SCHEMA:
                    if k not in self._conf.keys():
                        if isinstance(
                                ConfManager.BASE_SCHEMA[k], (list, dict)
                        ):
                            self._conf[k] = ConfManager.BASE_SCHEMA[k].copy()
                        else:
                            self._conf[k] = ConfManager.BASE_SCHEMA[k]
            except Exception as e:
                logging.warning("unknown conf error, resetting conf")
                self._conf = ConfManager.BASE_SCHEMA.copy()
                self.save_conf()
        else:
            logging.warning("no conf file found, creating")
            self._conf = ConfManager.BASE_SCHEMA.copy()
            self.save_conf()

    def save_conf(self):
        """
        Force save current configuration to disk
        """
        with open(str(self.path), 'w') as fd:
            fd.write(json.dumps(self._conf))

    def set_value(self, name: str, val: any):
        """
        Set a value in the configuration

        You do not need to use save_conf after this
        as it is done automatically.
        

        param:
            name: str name of the key, can be any json
            serializable object
            vaL: any json serializable value
        """
        self._conf[name] = copy.deepcopy(val)
        self.save_conf()

    def get_value(self, name: str) -> any:
        return self._conf[name]
