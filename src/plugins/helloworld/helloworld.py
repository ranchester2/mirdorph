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
from gi.repository import GObject, Peas

class HelloWorldPlugin(GObject.GObject, Peas.Activatable):
    __gtype_name__ = "HelloWorldPlugin"

    # For a standard activatable this is the application
    object = GObject.Property(type=GObject.GObject)

    def __init__(self):
        GObject.GObject.__init__(self)

    def do_activate(self):
        print("Hello World")

    def do_deactivate(self):
        print("Buy world")
