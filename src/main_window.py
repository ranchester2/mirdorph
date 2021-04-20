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
from .channel_inner_window import ChannelInnerWindow

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/main_window.ui')
class MirdorphMainWindow(Handy.ApplicationWindow, EventReceiver):
    __gtype_name__ = "MirdorphMainWindow"

    # temp for testing
    CHANNEL = 829659493708988449

    main_flap: Handy.Flap = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Handy.ApplicationWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.props.application.create_inner_window_context(self.CHANNEL)
        self.current_channel_inner_window = self.props.application.retrieve_inner_window_context(self.CHANNEL)
        self.current_channel_inner_window.show()
        self.main_flap.set_content(self.current_channel_inner_window)

        self.empty_inner_window = ChannelInnerWindow(empty=True)


    @Gtk.Template.Callback()
    def on_window_destroy(self, window):
        os._exit(1)

    def reconfigure_for_popout_window(self):
        """
        Configure the main win for a popout window

        This basically just makes sure the status page
        for no channel selected appears.

        NOTE: must be called AFTER you remove the channelcontext
        """
        self.main_flap.set_content(self.empty_inner_window)

    def unconfigure_for_popout_window(self):
        """
        Unconfigure the main win for a popout window

        This basically removes the status page
        for no channel selected.

        NOTE: must be called BEFORE you put your channelcontext
        back in
        """
        self.main_flap.remove(self.empty_inner_window)
        