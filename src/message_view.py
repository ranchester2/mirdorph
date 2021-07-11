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
import datetime
import sys
from gi.repository import Adw, Gtk, Gio, GObject, GLib
from .event_receiver import EventReceiver
from .message import MessageWidget, MessageMobject
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

    loading_history = GObject.Property(type=bool, default=False)

    _listview: Gtk.ListView = Gtk.Template.Child()

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
        # After first populating the listview, we appear at the top of the history,
        # not the bottom
        self._first_load = True

        self._model = Gio.ListStore()
        def data_sort_func(first: MessageMobject, second: MessageMobject, user_data):
            if first.created_at < second.created_at:
                return -1
            elif first.created_at > second.created_at:
                return 1
            else:
                return 0
        self._sorted_model = Gtk.SortListModel(
            model=self._model,
            sorter=Gtk.CustomSorter.new(data_sort_func)
        )

        # It is not simple to set a header widget of a listmodel, so instead we have
        # a flattened model containing the header model and then our real model.
        # The message Mobject also needs to be adapted to support this functionality
        # as all items must be of the same type
        self._header_model = Gio.ListStore()
        self._header_model.append(MessageMobject(None, is_header=True))
        model_list = Gio.ListStore()
        model_list.append(self._header_model)
        model_list.append(self._model)
        flattened_abstraction_model = Gtk.FlattenListModel.new(model_list)

        self._factory = Gtk.SignalListItemFactory()
        self._factory.connect("setup", self._data_setup)
        self._factory.connect("bind", self._data_bind)
        self._factory.connect("unbind", self._data_unbind)
        self._factory.connect("teardown", self._data_teardown)

        self._listview.set_model(Gtk.NoSelection.new(flattened_abstraction_model))
        self._listview.set_factory(self._factory)

        self._typing_indicator = TypingIndicator(self.context.channel_disc)
        self._typing_indicator_overlay.add_overlay(self._typing_indicator)

        self._adj = self.scroller.get_vadjustment()
        self._orig_upper = self._adj.get_upper()
        self._inserting_message = False
        # Autoscrolling is useful if for example you want to immediately see new
        # messages when they arrive and similar.
        self._autoscroll = False
        self._adj.connect("notify::upper", self._on_upper_changed)
        self._adj.connect("value-changed", self._on_adj_value_changed)

    def _data_setup(self, factor, listitem: Gtk.ListItem):
        listitem.set_child(MessageWidget())

    # Special handling of the header widget is required, which causes bind
    # to actually be equivelent to "setup" normally.
    def _data_bind(self, factor, listitem: Gtk.ListItem):
        if not listitem.get_item().is_header:
            listitem.get_child().do_bind(listitem.get_item())
        else:
            listitem.set_activatable(False)
            spinner = Gtk.Spinner()
            self.bind_property("loading-history", spinner, "spinning")
            listitem.set_child(spinner)

    def _data_unbind(self, factor, listitem: Gtk.ListItem):
        if isinstance(listitem.get_child(), MessageWidget):
            listitem.get_child().do_unbind()
        else:
            # When unbinding the header we have to recreate what setup does
            listitem.set_activatable(True)
            listitem.set_child(MessageWidget())

    def _data_teardown(self, factor, listitem: Gtk.ListItem):
        listitem.set_child(None)

    def _fix_merges(self):
        """
        Attempt to efficiently fix incorrect message merging,
        this only affects in correct mobjects and only itterates
        through the liststore once.

        It is needed because it is extremely hard to handle cross-load
        merging in `self._load_messages`, and this was the best solution
        that I found.
        """
        previous_mobject = None
        for mobject in self._model:
            if not previous_mobject:
                if mobject.get_property("merged"):
                    mobject.set_property("merged", False)
            elif previous_mobject.author == mobject.author:
                if not mobject.get_property("merged"):
                    mobject.set_property("merged", True)
            previous_mobject = mobject

    def filter_messages_dupes(self, messages: list) -> list:
        """
        Filter a list of `discord.Message` to only contain non-duplicates.

        param:
            messages: list of `discord.Message` to filter
        returns:
            a list of `discord.Message` that is not duplicated
        """
        ids = [message.id for message in messages]
        dupe_ids = []
        for item in self._model:
            if item.id in ids:
                dupe_ids.append(item.id)

        return [message for message in messages if message.id not in dupe_ids]

    def _load_messages(self, messages: list):
        """
        Load messages and create their widgets into the view
        from a list of discord message objects.

        param:
            messages - list of `discord.Message`. NOTE: all messages
            must be in a row as they actually are, you can't leave some out.
        """
        messages = self.filter_messages_dupes(messages)
        # Fallback, needed for merging
        messages.sort(key=lambda x : x.created_at)

        # Why list+splice? The performance is SIGNIFICANTLY
        # better when doing it like this
        message_widgets = []

        previous_author = None
        for message in messages:
            should_be_merged = False
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
                number_of = self._model.get_n_items()
                if number_of > 0:
                    last_mobject: MessageMobject = self._model.get_item(number_of - 1)
                    if message.created_at > last_mobject.created_at:
                        # The message here can be from anywhere, we want to avoid
                        # blindly assuming it will be the latest message.
                        should_be_merged = (message.author == last_mobject.author)

            message_widgets.append(MessageMobject(message, merged=should_be_merged))
            previous_author = message.author

        # Workaround: https://gitlab.gnome.org/GNOME/gtk/merge_requests/395
        self.scroller.set_kinetic_scrolling(False)
        self._model.splice(0, 0, message_widgets)
        if self._first_load:
            GLib.idle_add(self.context.scroll_messages_to_bottom)

        if messages:
            self._fix_merges()

        self._first_load = False

    def _on_upper_changed(self, upper: float, adjparam):
        self.scroller.set_kinetic_scrolling(True)
        if self._autoscroll:
            # When using listbox this caused issues as the vadjustment
            # hadn't been updated with the new upper
            GLib.idle_add(self._adj.set_value, self._adj.get_upper())

    def _on_adj_value_changed(self, adj):
        self._autoscroll = self.context.is_scroll_at_bottom
        self._scroll_btn_revealer.set_reveal_child(not self.context.is_scroll_at_bottom)

        # Near top of loaded history
        if adj.get_value() < adj.get_page_size() * 2:
            if not self.props.loading_history:
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

    async def _get_history_messages_to_list(self, channel: discord.TextChannel, amount_to_load: int, before: datetime.datetime=None) -> list:
        """
        Return a list of Discord messages in current history,
        useful to call in other thread and use the list to build
        message widgets.

        param:
            channel: the discord channel
            amount_to_load: how many messages you want to get,
            before: if it exists, before which message to load
        """
        if before:
            messages = await channel.history(limit=amount_to_load, before=before).flatten()
        else:
            messages = await channel.history(limit=amount_to_load).flatten()
        return messages

    def _history_loading_gtk_target(self, messages: list):
        self._load_messages(messages)

        self.props.loading_history = False

    def _history_loading_target(self, additional: None, before: None):
        # Additional is only there if we want to "add" to the history,
        # and before is also only if we want to "add" to the history,
        # not start from scratch. Which is why we have to change the amount
        # passed to the getting messages history function.
        if before:
            amount_to_load = additional
        else:
            amount_to_load = self._STANDARD_HISTORY_LOADING

        messages = asyncio.run_coroutine_threadsafe(
            self._get_history_messages_to_list(
                self.context.channel_disc,
                amount_to_load,
                before=before
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
        if self.props.loading_history:
            logging.warning("attempted to load history even if already loading")
            return
        self.props.loading_history = True
        # Better to get here to avoid GLib.ilde_add, as the model can only be used
        # on the main thread.
        if additional:
            before = self._model.get_item(0).created_at
        else:
            before = None
        threading.Thread(target=self._history_loading_target, args=(additional, before,)).start()
