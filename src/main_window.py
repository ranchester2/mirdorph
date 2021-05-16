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
class MirdorphMainWindow(Handy.ApplicationWindow):
    __gtype_name__ = "MirdorphMainWindow"

    main_flap: Handy.Flap = Gtk.Template.Child()
    # Public, the contexts themselves interact with the stack to manage popout and similar
    context_stack: Gtk.Stack = Gtk.Template.Child()
    _flap_box: Gtk.Box = Gtk.Template.Child()

    _main_menu_popover: Gtk.Popover = Gtk.Template.Child()
    _main_menu_button: Gtk.Button = Gtk.Template.Child()

    _add_server_button: Gtk.ToggleButton = Gtk.Template.Child()

    _notification_revealer: Gtk.Revealer = Gtk.Template.Child()
    _notification_label: Gtk.Label = Gtk.Template.Child()
    _notification_title_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Handy.ApplicationWindow.__init__(self, *args, **kwargs)

        menu_builder = Gtk.Builder.new_from_resource(
            '/org/gnome/gitlab/ranchester/Mirdorph/ui/general_menu.ui'
        )
        menu = menu_builder.get_object('generalMenu')
        self._main_menu_popover.bind_model(menu)

        self._empty_inner_window = ChannelInnerWindow(empty=True)
        self.main_flap.connect("notify::folded", self._empty_inner_window.handle_flap_folding)
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

    def _setting_switching_focus_gtk_target(self, context):
        try:
            context.do_first_see()
        except AttributeError:
            logging.warning("impossible to set default focus of empty status context")

    @Gtk.Template.Callback()
    def _on_context_stack_focus_change(self, stack, strpar):
        # I have been trying to set the default focus when swithing to a child to be the entry bar
        # However, in most places it just DOESN'T WORK (the function is called though.
        # It seems that it only works if you wait for GTK to finish whatever its doing. Like
        # to finish loading channel history. Here, it must be in a GLib.idle_add for whatever
        # reaso
        GLib.idle_add(self._setting_switching_focus_gtk_target, stack.get_visible_child())

        try:
            stack.get_visible_child().load_history()
        except AttributeError:
            logging.warning("impossible to load history of empty status context")

    @Gtk.Template.Callback()
    def _on_window_destroy(self, window):
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
        """
        Display a specifed channel to the user

        param:
            channel_id: int of the channel that you want
            to display
        """

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
            # Temp hack to get it to work when switching channels in mobile
            # mode
            context.handle_flap_folding(self.main_flap, None)

            self.context_stack.set_visible_child(context)
            # For making the entry the default focus
            context.do_first_see()
            
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

    @Gtk.Template.Callback()
    def _on_notification_button_clicked(self, button):
        self._notification_revealer.set_reveal_child(False)

    def display_err_priv(self, error_title: str, error_body: str):
        self._notification_label.set_label(error_body)
        self._notification_title_label.set_label(error_title)
        self._notification_revealer.set_reveal_child(True)

        # For automatically closing the notification
        threading.Thread(target=self._notification_waiting_target).start()

    def _notification_waiting_target(self):
        time.sleep(5)
        GLib.idle_add(self._notification_waiting_gtk_target)

    def _notification_waiting_gtk_target(self):
        self._notification_revealer.set_reveal_child(False)
