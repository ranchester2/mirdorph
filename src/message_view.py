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

import asyncio
import logging
import threading
import discord
import sys
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Handy
from .event_receiver import EventReceiver
from .message import MirdorphMessage
from .typing_indicator import TypingIndicator


# From clutter-easing.c, based on Robert Penner's
# infamous easing equations, MIT license.
def ease_out_cubic(t: float) -> float:
    p = t - float(1);
    return (p * p * p + float(1))


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message_view.ui')
class MessageView(Gtk.Overlay, EventReceiver):
    __gtype_name__ = "MessageView"

    _STANDARD_HISTORY_LOADING = 40

    _message_column: Gtk.Box = Gtk.Template.Child()
    # Originally code was designed with message_view inheriting from
    # Gtk.ScrolledWindow, however since now that isn't the case, and people
    # expect to access this instead, we use it by making it public
    scroller: Gtk.ScrolledWindow = Gtk.Template.Child()

    _scroll_btn_revealer: Gtk.Revealer = Gtk.Template.Child()
    _typing_indicator_overlay: Gtk.Overlay = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.Overlay.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self.context = context

        self._message_listbox = Gtk.ListBox(hexpand=True, selection_mode=Gtk.SelectionMode.NONE)
        # When nearly empty channel, messages should not pile up on top
        self._message_listbox.set_valign(Gtk.Align.END)
        self._message_listbox.get_style_context().add_class("message-history")

        # Due to events, the messages might often become out of order
        # this ensures that the messages that were created earlier
        # are always displayed *before* the later ones. This is for history
        def message_listbox_sort_func(row_1, row_2, data, notify_destroy):
            # For history loading spinner, which is a special case
            if not isinstance(row_1, MirdorphMessage) or not isinstance(row_2, MirdorphMessage):
                return -1
            if row_1.timestamp < row_2.timestamp:
                return -1
            else:
                return (row_1.timestamp < row_2.timestamp) + 1

        self._message_listbox.set_sort_func(message_listbox_sort_func, None, False)
        self._message_listbox.show()

        self._history_loading_row = Gtk.ListBoxRow(height_request=32)
        self._history_loading_row.show()
        self._history_loading_spinner = Gtk.Spinner()
        self._history_loading_spinner.show()
        self._history_loading_row.add(self._history_loading_spinner)
        self._message_listbox.add(self._history_loading_row)

        self._message_clamp = Handy.Clamp(maximum_size=800, tightening_threshold=600)
        self._message_clamp.show()
        self._message_clamp.add(self._message_listbox)
        self._message_column.add(self._message_clamp)

        self._typing_indicator = TypingIndicator(self.context.channel_disc)
        self._typing_indicator.show()
        self._typing_indicator_overlay.add_overlay(self._typing_indicator)

        self._adj = self.scroller.get_vadjustment()
        self._orig_upper = self._adj.get_upper()
        self._balance = None
        self._autoscroll = False
        # When the attachment tray is revealed we want a smooth animation,
        # this basically signifies if that animation is active and we should
        # always auto scroll
        self._attachment_tray_scroll_revealment_mode = False

    def set_balance_top(self):
        # DONTFIXME: Workaround: https://gitlab.gnome.org/GNOME/gtk/merge_requests/395
        self.scroller.set_kinetic_scrolling(False)
        self._balance = Gtk.PositionType.TOP

    def _handle_upper_adj_notify(self, upper, adjparam):
        new_upper = self._adj.get_upper()
        diff = new_upper - self._orig_upper

        if self._attachment_tray_scroll_revealment_mode:
            self._adj.set_value(self._adj.get_upper())

        # Don't do anything if upper didn't change
        if diff != 0.0:
            self._orig_upper = new_upper
            if self._autoscroll:
                self._adj.set_value(self._adj.get_upper() - self._adj.get_page_size())
            elif self._balance == Gtk.PositionType.TOP:
                self._balance = False
                self._adj.set_value(self._adj.get_value() + diff)
                self.scroller.set_kinetic_scrolling(True)

    def _handle_value_adj_changed(self, adj):
        self._autoscroll = self.context.precise_is_scroll_at_bottom
        self._scroll_btn_revealer.set_reveal_child(not self.context.precise_is_scroll_at_bottom)

        if adj.get_value() < adj.get_page_size() * 1.5:
            self.load_history(additional=15)


    ### Smooth Scrolling code taken from Fractal, but converted from rust to Python ###
    ### I don't know how it works, its magic. And I don't even know Rust, but it seems to work ###
    def _scroll_down_tick_callback(self, scroller, clock, start_time, end_time, start):
        now = clock.get_frame_time()
        end = self._adj.get_upper() - self._adj.get_page_size()
        if now < end_time and abs((round(self._adj.get_value()) - round(end))) > sys.float_info.epsilon:
            t = float(now - start_time) / float(end_time - start_time)
            t = ease_out_cubic(t)
            self._adj.set_value(start + t * (end - start))
            return GLib.SOURCE_CONTINUE
        else:
            self._adj.set_value(end)
            return GLib.SOURCE_REMOVE

    def _scroll_down_animated(self):
        clock = self.scroller.get_frame_clock()
        duration = 200
        start = self._adj.get_value()
        start_time = clock.get_frame_time()
        end_time = start_time + 1000 * duration
        self.scroller.add_tick_callback(
            self._scroll_down_tick_callback,
            start_time,
            end_time,
            start
        )

    def build_scroll(self):
        self._adj.connect("notify::upper", self._handle_upper_adj_notify)
        self._adj.connect("value-changed", self._handle_value_adj_changed)

    def _on_msg_send_mode_scl_send_wrap(self):
        self.context.scroll_messages_to_bottom()

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel_id:
            last_message = self._message_listbox.get_children()[-1]
            if isinstance(last_message, MirdorphMessage):
                should_be_merged = (message.author == last_message.author)
            else:
                should_be_merged = False
            message_wid = MirdorphMessage(
                message,
                merged=should_be_merged
            )
            message_wid.show()

            # No risk of this being a duplicate as this event never happens twice
            self._message_listbox.add(message_wid)

            if self.context.is_scroll_for_msg_send or self.context.is_scroll_at_bottom:
                # With GLIB.idle_add and a wrapper instead of directly,
                # since for some reason it only works like this.
                GLib.idle_add(self._on_msg_send_mode_scl_send_wrap)

            # We unset it here since currently it always intended for one message - the next one
            # And it is extremely unlikely that the next on_message isn't the one that has been sent.
            # This isnt called in the async send msg function with GLib.idle_add because it for some
            # reason executes in the wrong order then and misses the message
            # However this now be a bit different (seems a bit more accurate) with the additional
            # Fractal scrolling code.
            self.context.unprepare_scroll_for_msg_send()

    @property
    def history_loading_is_complete(self):
        """
        If history loading has completed atleast once

        This is useful for calling something that depends on history getting loaded,
        like scrolling the messages to the bottom for the first time. Not 100% accurate
        """
        # Works as the message listboxes are direct children of the message listbox
        # However not 100% accurate as some could have been from on_message,
        # but that is highly unlikely
        for child in self._message_listbox.get_children():
            if isinstance(child, MirdorphMessage):
                return True
        return False

    async def _get_history_messages_to_list(self, channel, amount_to_load):
        """
        Return a list of Discord messages in current history,
        useful to call in other thread and use the list to build
        message objects
        """
        tmp_list = []
        async for message in channel.history(limit=amount_to_load):
            tmp_list.append(message)
        return tmp_list

    def _history_loading_gtk_target(self, messages: list):
        previous_message_author = None

        for message in messages:
            # We need to check for duplicates and not add it if it is one
            # because load_history will often be called multiple times
            duplicate = False
            # The message listbox currently just has messages directly as children
            # so this work fine
            for already_existing_message in self._message_listbox.get_children():
                if (isinstance(already_existing_message, MirdorphMessage) and
                    message.id == already_existing_message.uniq_id):
                        duplicate = True
                        break
            if not duplicate:

                message_wid = MirdorphMessage(
                    message,
                    merged=(previous_message_author == message.author)
                )
                previous_message_author = message.author
                message_wid.show()
                self.set_balance_top()
                self._message_listbox.add(message_wid)

        self._history_loading_spinner.stop()
        self.context.signify_stopped_loading_hs()

    def _history_loading_target(self, additional):
        amount_to_load = self._STANDARD_HISTORY_LOADING
        if additional is not None:
            amount_to_load = len(self._message_listbox.get_children()) + additional

        messages = list(
            asyncio.run_coroutine_threadsafe(
                self._get_history_messages_to_list(
                    self.context.channel_disc,
                    amount_to_load
                ),
                Gio.Application.get_default().discord_loop
            ).result()
        )

        GLib.idle_add(self._history_loading_gtk_target, messages)

    def load_history(self, additional=None):
        """
        Load the history of the view and it's channel

        You can only load once at a time, async operation

        param:
            additional - additional ammount of messages to load, useful
            only if previously loaded
        """
        if self.context.is_loading_history:
            logging.warning("attempted to load history even if already loading")
            return
        self.context.signify_loading_hs()
        self._history_loading_spinner.start()
        message_loading_thread = threading.Thread(target=self._history_loading_target, args=(additional,))
        message_loading_thread.start()

    @Gtk.Template.Callback()
    def _on_scroll_btn_clicked(self, button):
        self._scroll_btn_revealer.set_reveal_child(False)
        self._scroll_down_animated()

