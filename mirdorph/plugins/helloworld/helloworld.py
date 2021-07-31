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

import gi
from gi.repository import Gio, GObject
from mirdorph.plugin import MrdApplicationPlugin

class HelloWorldPlugin(MrdApplicationPlugin):
    def __init__(self):
        super().__init__()
        self._welcome_message = Gio.resources_lookup_data(
            "/org/gnome/gitlab/ranchester/Mirdorph/plugins/helloworld/welcome_message.txt", 0
        ).get_data().decode("utf-8")

    def load(self):
        print(self._welcome_message)

    def unload(self):
        print("Bye, World!")
