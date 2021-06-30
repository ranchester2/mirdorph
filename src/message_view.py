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
from gi.repository import Gtk, Gio, GLib, Handy
from .event_receiver import EventReceiver
from .message import MirdorphMessage
from .typing_indicator import TypingIndicator


# From clutter-easing.c, based on Robert Penner's
# infamous easing equations, MIT license.
def ease_out_cubic(t: float) -> float:
    p = t - float(1)
    return (p * p * p + float(1))


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/message_view.ui")
class MessageView(Gtk.Overlay, EventReceiver):
    __gtype_name__ = "MessageView"

    _STANDARD_HISTORY_LOADING = 40

    _message_column: Gtk.Box = Gtk.Template.Child()
    # Originally code was designed with message_view inheriting from
    # Gtk.ScrolledWindow, however since now that isn't the case, and people
    # expect to access this, we use it by making it public
    scroller: Gtk.ScrolledWindow = Gtk.Template.Child()

    _scroll_btn_revealer: Gtk.Revealer = Gtk.Template.Child()
    _typing_indicator_overlay: Gtk.Overlay = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.Overlay.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self.context = context
        self.app = Gio.Application.get_default()
        self._loading_history = False

        self._message_listbox = Gtk.ListBox(hexpand=True, selection_mode=Gtk.SelectionMode.NONE)
        self._message_listbox.get_style_context().add_class("message-history")
        # With nearly empty channel, messages should not pile up on top
        self._message_listbox.set_valign(Gtk.Align.END)
        # It is better to always ensure the order is correct, instead of manually fidling with
        # it when adding children.
        def message_listbox_sort_func(row_1, row_2, data, notify_destroy):
            # The history row should always be at the end
            if hasattr(row_1, "is_history_row"):
                return -1

            if row_1.timestamp < row_2.timestamp:
                return -1
            elif row_1.timestamp > row_2.timestamp:
                return 1
            else:
                return 0
        self._message_listbox.set_sort_func(message_listbox_sort_func, None, False)
        self._message_listbox.show()

        self._history_loading_row = Gtk.ListBoxRow(height_request=32)
        # Attribute makes detecting it in sort easy
        self._history_loading_row.is_history_row = True
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
        self._inserting_message = False
        # Autoscrolling is useful if for example you want to immediately see new
        # messages when they arrive and similar.
        self._autoscroll = False
        self._adj.connect("notify::upper", self._on_upper_changed)
        self._adj.connect("value-changed", self._on_adj_value_changed)

        self._message_listbox.set_focus_vadjustment(self._adj)

    def _fix_merges(self):
        """
        Attempt to efficiently fix incorrect message merging,
        this only affects in correct rows and only itterates
        through the listbox once.

        It is needed because it is extremely hard to handle cross-load
        merging in `self._load_messages`, and this was the best solution
        that I found.
        """
        previous_row = None
        for row in self._message_listbox.get_children():
            if hasattr(row, "author") and hasattr(row, "merged"):
                if not previous_row:
                    if row.merged:
                        row.unmerge()
                elif previous_row.author == row.author:
                    if not row.merged:
                        row.merge()
                previous_row = row

    def remove_ad(self, row: Gtk.Widget):
        """
        Remove a row, advanced helper function
        """
        self._message_listbox.remove(row)

    def add_ad(self, row: Gtk.Widget):
        """
        Add a row, advanced helper function.

        The main reason is for there to be a unified function
        for updating the contents, and this is useful to
        for example automatically handle scorlling.

        param:
            row - the row to add.
        """
        # Workaround: https://gitlab.gnome.org/GNOME/gtk/merge_requests/395
        self.scroller.set_kinetic_scrolling(False)
        # The added widget is expected to change the size of the listbox,
        # causing the handling of the ::notify::upper signal to revert this
        # when needed.
        self._inserting_message = True

        self._message_listbox.add(row)

    def object_is_dupe(self, new_id: int) -> bool:
        """
        Figure out if adding a row based on this object will be
        a dupe.
        param:
            new_id - the unique discord event id for what is being added.
        """
        for row in self._message_listbox.get_children():
            if hasattr(row, "disc_id"):
                if new_id == row.disc_id:
                    return True
        return False

    def _load_messages(self, messages: list):
        """
        Load messages and create their widgets into the view
        from a list of discord message objects.

        param:
            messages - list of `discord.Message`. NOTE: all messages
            must be in a row as they actually are, you can't leave some out.
        """
        # Fallback, sorting errors more likely than unhandled holes.
        messages.sort(key=lambda x : x.created_at)

        previous_author = None
        for message in messages:
            if not self.object_is_dupe(message.id):
                if previous_author:
                    should_be_merged = (previous_author == message.author)
                # When adding only a single message, for example on send,
                # we really want to avoid merging/unmerging the message
                # after it is already displayed, as that will be needed
                # 100% of the time.
                # Fractal has an issue about this:
                # https://gitlab.gnome.org/GNOME/fractal/-/issues/231
                # we work around it ;)
                elif len(messages) == 1:
                    last_row = self._message_listbox.get_children()[-1]
                    if hasattr(last_row, "timestamp") and hasattr(last_row, "author"):
                        # The message here can be from anywhere, we want to avoid
                        # blindly assuming it will be the latest message.
                        if message.created_at.timestamp() > last_row.timestamp:
                            should_be_merged = (last_row.author == message.author)
                else:
                    should_be_merged = False

                message_wid = MirdorphMessage(
                    message,
                    merged=should_be_merged
                )
                message_wid.show()
                self.add_ad(message_wid)
                previous_author = message.author

        if messages:
            # This can change the size of the listbox,
            # however no time for the GLib loop to process idle events
            # (update the scroll position) is between adding the rows
            # and fixing the merges.
            self._fix_merges()

    def _on_upper_changed(self, upper: float, adjparam):
        new_upper = self._adj.get_upper()
        diff = new_upper - self._orig_upper

        if self.context.attachment_tray_scroll_mode:
            self._adj.set_value(self._adj.get_upper())

        if diff != 0.0:
            self._orig_upper = new_upper
            if self._autoscroll:
                self._adj.set_value(self._adj.get_upper() - self._adj.get_page_size())
            # Keeping scroll position when loading extra content
            elif self._inserting_message:
                self._adj.set_value(self._adj.get_value() + diff)
                self.scroller.set_kinetic_scrolling(True)
                self._inserting_message = False

    def _on_adj_value_changed(self, adj):
        self._autoscroll = self.context.is_scroll_at_bottom
        self._scroll_btn_revealer.set_reveal_child(not self.context.is_scroll_at_bottom)

        # Near top of loaded history
        if adj.get_value() < adj.get_page_size() * 1.5:
            self.load_history(additional=15)

    ### Smooth scroll animation code taken from Fractal, but converted from rust to Python
    ### Also, I basically know zero Rust ###
    ### I don't know how it works, its magic. ###
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

    @Gtk.Template.Callback()
    def _on_scroll_btn_clicked(self, button):
        self._scroll_btn_revealer.set_reveal_child(False)
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

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel_id:
            self._load_messages([message])

            if self.context.scroll_for_msg_send:
                GLib.idle_add(self.context.scroll_messages_to_bottom)

            # We unset it here since currently it always intended for one message - the next one
            # And it is extremely unlikely that the next on_message isn't the one that has been sent.
            # This isnt called in the async send msg function with GLib.idle_add because it for some
            # reason executes in the wrong order then and misses the message.
            self.context.scroll_for_msg_send = False

    async def _get_history_messages_to_list(self, channel: discord.TextChannel, amount_to_load: int) -> list:
        """
        Return a list of Discord messages in current history,
        useful to call in other thread and use the list to build
        message widgets.

        param:
            channel: the discord channel
            amount_to_load: how many messages you want to get (from history start)
        """
        return [message async for message in channel.history(limit=amount_to_load)]

    def _history_loading_gtk_target(self, messages: list):
        self._load_messages(messages)

        self._history_loading_spinner.stop()
        self._loading_history = False

    def _history_loading_target(self, additional):
        amount_to_load = self._STANDARD_HISTORY_LOADING
        if additional is not None:
            amount_to_load = len(
                [wid for wid in self._message_listbox.get_children() if isinstance(wid, MirdorphMessage)]
            ) + additional

        messages = asyncio.run_coroutine_threadsafe(
            self._get_history_messages_to_list(
                self.context.channel_disc,
                amount_to_load
            ),
            self.app.discord_loop
        ).result()

        GLib.idle_add(self._history_loading_gtk_target, messages)

    def load_history(self, additional=None):
        """
        Load the history of the view and it's channel

        You can only load once at a time, async operation.

        param:
            additional - additional ammount of messages to load, useful
            only if previously loaded, for example more history when scrolling.
        """
        if self._loading_history:
            logging.warning("attempted to load history even if already loading")
            return
        self._loading_history = True
        self._history_loading_spinner.start()
        threading.Thread(target=self._history_loading_target, args=(additional,)).start()
