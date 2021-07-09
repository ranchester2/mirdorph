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
import logging
import threading
import queue
import time
from gi.repository import Adw, Gtk, GLib
from .event_receiver import EventReceiver
from .channel_inner_window import ChannelInnerWindow
from .channel_sidebar import MirdorphChannelSidebar

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/main_window.ui")
class MirdorphMainWindow(Adw.ApplicationWindow, EventReceiver):
    __gtype_name__ = "MirdorphMainWindow"

    _loading_stack: Gtk.Stack = Gtk.Template.Child()
    _loading_progress_bar: Gtk.ProgressBar = Gtk.Template.Child()

    main_flap: Adw.Flap = Gtk.Template.Child()
    # Public, the contexts themselves interact with the stack to manage popout and popin
    context_stack: Gtk.Stack = Gtk.Template.Child()
    _flap_box: Gtk.Box = Gtk.Template.Child()

    _channel_search_button: Gtk.ToggleButton = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Adw.ApplicationWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self._empty_inner_window = ChannelInnerWindow(empty=True)
        self.main_flap.connect("notify::folded", self._empty_inner_window.handle_flap_folding)
        self.context_stack.add_child(self._empty_inner_window)

        self._channel_sidebar = MirdorphChannelSidebar(channel_search_button=self._channel_search_button, vexpand=True)
        self._flap_box.append(self._channel_sidebar)

        GLib.timeout_add(150, self._progress_bar_target)

    def _progress_bar_target(self):
        self._loading_progress_bar.pulse()
        # We want it to stop pulsing when loading has stopped
        return self._loading_stack.get_visible_child_name() == "loading"

    def disc_on_ready(self, *args):
        # on_ready shows that overall we are connected, and client.guilds
        # becomes available
        self._loading_stack.set_visible_child_name("session")

    def _setting_switching_focus_gtk_target(self, context):
        try:
            context.do_first_see()
        except AttributeError:
            logging.warning("impossible to set default focus of empty status context")

    @Gtk.Template.Callback()
    def _on_loading_close_btn_clicked(self, button):
        self.destroy()

    @Gtk.Template.Callback()
    def _on_context_stack_focus_change(self, stack, strpar):
        # I have been trying to set the default focus when swithing to a child to be the entry bar
        # However, you can't do it here, as you need to wait for GTK to finish everything,
        # which is why GLib.idle_add. And also why the standard focus APIs don't work,
        # as the channel is displayed down the line.
        GLib.idle_add(self._setting_switching_focus_gtk_target, stack.get_visible_child())

        try:
            stack.get_visible_child().load_history()
        except AttributeError:
            logging.warning("impossible to load history of empty status context")

    @Gtk.Template.Callback()
    def _on_window_close(self, window):
        # Dangerous, but we need to kill all threads instantly for now
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
        """
        Unconfigure the main win for a popout window

        This basically adds it back to the stack and makes it
        the currently displayed one

        param:
            context - the ChannelInnerWindow context
        """
        self.context_stack.add_child(context)
        self.context_stack.set_visible_child(context)

    def show_active_channel(self, channel_id):
        """
        Display a specifed channel to the user

        param:
            channel_id: int of the channel that you want
            to display
        """
        context = self.props.application.retrieve_inner_window_context(channel_id)
        if context.is_poped:
            temp_win_top = context.get_native()
            if temp_win_top:
                temp_win_top.present()

            # May seem weird to use it here, however without it the previous channel
            # is shown, and the channel selection breaks.
            self.reconfigure_for_popout_window()
        else:
            # Temp hack to get it to work when switching channels in mobile
            # mode
            context.handle_flap_folding(self.main_flap, None)

            self.context_stack.set_visible_child(context)
            # For making the entry the default focus
            context.do_first_see()

