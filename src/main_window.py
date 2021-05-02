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
from .channel_sidebar import MirdorphChannelSidebar

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/main_window.ui')
class MirdorphMainWindow(Handy.ApplicationWindow, EventReceiver):
    __gtype_name__ = "MirdorphMainWindow"

    main_flap: Handy.Flap = Gtk.Template.Child()
    # Public, the contexts themselves interact with the stack to manage popout and similar
    context_stack: Gtk.Stack = Gtk.Template.Child()
    _flap_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Handy.ApplicationWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        # Could be better than basically making this global
        self.props.application.bar_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)

        self._empty_inner_window = ChannelInnerWindow(empty=True)
        self._empty_inner_window.show()
        self.context_stack.add(self._empty_inner_window)

        # Might be a bit weird to be public.
        # However this needs to be used in main's connect
        # and add channel functions.
        # Would be better if instead of working on the channel sidebar correctly
        # we had a channel manager object
        self.channel_sidebar = MirdorphChannelSidebar()
        self.channel_sidebar.show()
        self._flap_box.pack_end(self.channel_sidebar, True, True, 0)


    @Gtk.Template.Callback()
    def _on_window_destroy(self, window):
        os._exit(1)

    def reconfigure_for_popout_window(self):
        """
        Configure the main win for a popout window

        This basically just makes sure the status page
        for no channel selected appears.

        NOTE: must be called AFTER you remove the channelcontext
        """
        self.context_stack.set_visible_child(self._empty_inner_window)

    def unconfigure_popout_window(self, context):
       self.context_stack.add(context)
       self.context_stack.set_visible_child(context)

    def show_active_channel(self, channel_id):
        context = self.props.application.retrieve_inner_window_context(channel_id)
        if context.is_poped:
            temp_win_top = context.get_toplevel()
            # Function name misleading
            if temp_win_top.is_toplevel():
                temp_win_top.present()

            # May seem weird to use it here, however if we don't make it look
            # like there is no channel selected, then the previous channel is shown
            self.reconfigure_for_popout_window()
        else:
            self.context_stack.set_visible_child(context)
            
