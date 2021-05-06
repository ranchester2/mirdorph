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
from gi.repository import Gtk, Handy, Gio, GLib
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

    _add_server_button: Gtk.ToggleButton = Gtk.Template.Child()
    _basic_add_channel_popover: Gtk.Popover = Gtk.Template.Child()
    _add_channel_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Handy.ApplicationWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        # Could be better than basically making this global
        self.props.application.bar_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)

        self._empty_inner_window = ChannelInnerWindow(empty=True)
        self._empty_inner_window.show()
        self.context_stack.add(self._empty_inner_window)


        # This is so that we could know when was the first time channel was selected
        # and then scroll to bottom. For show_active_channel
        self._previously_selected_channels = [

        ]

        # Might be a bit weird to be public.
        # However this needs to be used in main's connect
        # and add channel functions.
        # Would be better if instead of working on the channel sidebar correctly
        # we had a channel manager object
        self.channel_sidebar = MirdorphChannelSidebar()
        self.channel_sidebar.show()
        self._flap_box.pack_end(self.channel_sidebar, True, True, 0)

    @Gtk.Template.Callback()
    def _on_add_server_button_toggled(self, button):
        if button.get_active():
            self._basic_add_channel_popover.popup()
        else:
            self._basic_add_channel_popover.popdown()

    @Gtk.Template.Callback()
    def _on_basic_add_channel_popover_closed(self, popover):
        self._add_server_button.set_active(False)

    @Gtk.Template.Callback()
    def _on_add_channel_entry_activate(self, entry):
        new_chan_id = int(entry.get_text())
        entry.set_text('')
        new_tmp_curr_chan_list = self.props.application.confman.get_value("added_channels")
        new_tmp_curr_chan_list.append(new_chan_id)
        self.props.application.confman.set_value("added_channels", new_tmp_curr_chan_list)
        self.props.application.reload_channels(
            self.props.application.confman.get_value("added_channels")
        )

    @Gtk.Template.Callback()
    def _on_context_stack_focus_change(self, stack, strpar):
        try:
            stack.get_visible_child().load_history()
        except AttributeError:
            logging.warning("impossible to load history of empty status context")

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

    def _is_channel_selected_first_time(self, channel_id):
        return (True if (channel_id not in self._previously_selected_channels) else False)

    def _setting_messages_to_bottom_first_time_target(self, channel_id):
        stop_qu = queue.Queue()
        while True:
            try:
                is_compl = stop_qu.get(timeout=0.1)
                if is_compl:
                    return
            except queue.Empty:
                pass

            time.sleep(0.1)
            GLib.idle_add(
                self._setting_messages_to_bottom_check_and_run_gtk_target,
                channel_id,
                stop_qu
            )

    def _setting_messages_to_bottom_check_and_run_gtk_target(self, channel_id, stop_qu):
        context = self.props.application.retrieve_inner_window_context(channel_id)
        if context.history_loading_is_complete:
            context.scroll_messages_to_bottom()
            stop_qu.put(True)


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
            
        if self._is_channel_selected_first_time(channel_id):
            self._previously_selected_channels.append(channel_id)

            # Because loading channels is in another thread, we cannot directly
            # try scrolling the messages here as it might not have finished yet
            # which is why we create another thread that continually checks if it has completed
            stop_thread = False

            setting_messages_to_bot_thread = threading.Thread(
                target=self._setting_messages_to_bottom_first_time_target,
                args=(channel_id,)
            )
            setting_messages_to_bot_thread.start()
