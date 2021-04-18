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

import os
from gi.repository import Gtk, Handy, Gio
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/main_window.ui')
class MirdorphMainWindow(Handy.ApplicationWindow, EventReceiver):
    __gtype_name__ = "MirdorphMainWindow"

    def __init__(self, *args, **kwargs):
        Handy.ApplicationWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

    @Gtk.Template.Callback()
    def on_window_destroy(self, window):
        os._exit(1)

    def disc_on_message(self, message):
        print(message.content)