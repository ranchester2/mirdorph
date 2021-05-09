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
from gi.repository import Gtk, Handy, Gio, GLib
from .event_receiver import EventReceiver


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_inner_window.ui')
class ChannelInnerWindow(Gtk.Box, EventReceiver):
    __gtype_name__ = "ChannelInnerWindow"

    _context_headerbar: Handy.HeaderBar = Gtk.Template.Child()

    _toplevel_empty_stack: Gtk.Stack = Gtk.Template.Child()
    _empty_status_page: Handy.StatusPage = Gtk.Template.Child()

    _content_box: Gtk.Box = Gtk.Template.Child()

    _popout_button_stack: Gtk.Stack = Gtk.Template.Child()
    _popout_button: Gtk.Button = Gtk.Template.Child()
    _popin_button: Gtk.Button = Gtk.Template.Child()

    _flap_toggle_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel=None, empty=True, *args, **kwargs):
        """
        Create a new ChannelInnerWindow. NOTE: don't use this, use
        that of your application instead.

        param:
            channel: channel id that this context uses (note: if none empty is on)
            empty: if this is just an empty state for its status message
        """
        
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self.app = Gio.Application.get_default()
        self.channel_id = channel
        self.empty = empty
        if self.channel_id is None:
            self.empty = True

        self.is_poped = False

        if not self.empty:
            # Blocking
            self.channel_disc = asyncio.run_coroutine_threadsafe(
                self.app.discord_client.fetch_channel(self.channel_id),
                self.app.discord_loop
            ).result()

            self._context_headerbar.set_title("#" + self.channel_disc.name)
            if self.channel_disc.topic is not None:
                self._context_headerbar.set_subtitle(self.channel_disc.topic)

            self._message_view = MessageView(context=self)
            self._message_view.show()
            self._content_box.pack_start(self._message_view, True, True, 0)

            self._message_entry_bar = MessageEntryBar(context=self)
            self._message_entry_bar.show()

            self._msg_sending_scrl_mode_en = False

            self._content_box.pack_end(self._message_entry_bar, False, False, 0)
            self._content_box.pack_end(Gtk.Separator(visible=True), False, False, 0)
        elif self.empty:
            self._popout_button.destroy()
            self._popin_button.destroy()
            self._popout_button_stack.destroy()
            self._toplevel_empty_stack.set_visible_child(self._empty_status_page)

    # Would be better to move this to main_win instead,
    # this is curently temp as we need to popin, however
    # we could just go through the list of channel contexts.
    def handle_flap_folding(self, flap, folded):
        if flap.get_folded():
            self._flap_toggle_button.set_visible(True)
            self._popout_button_stack.set_visible(False)
            flap.set_swipe_to_close(True)

            self.popin()
        else:
            self._flap_toggle_button.set_visible(False)
            self._popout_button_stack.set_visible(True)
            flap.set_swipe_to_close(False)

    # wrapper to load history in the messageview for message sending
    def load_history(self):
        self._message_view.load_history()

    # Could be better if this was defined in message_view instead?
    @property
    def is_loading_history(self):
        # Since we know that the history_loading_spinner
        # only exists while messages are currently being loaded,
        # we can use it as an indicator to test if to try loading or not
        # as this can be easily triggered many times
        try:
            self._message_view._history_loading_spinner
        except AttributeError:
            return False
        else:
            return True

    @property
    def history_loading_is_complete(self):
        """
        Wrapper around message view's is history loading complete
        """

        return self._message_view.history_loading_is_complete


    def scroll_messages_to_bottom(self):
        """
        Scroll the view to the very bottom

        NOTE: you need to add to this box BEFORE you scroll
        if you wish to go to the real bottom
        """

        adj = self._message_view.get_vadjustment()
        adj.set_value(adj.get_upper())

    @property
    def is_scroll_at_bottom(self):
        """
        Is the user currently scrolled to the very bottom of the
        view
        """
        adj = self._message_view.get_vadjustment()
        # We can't check for it exactly, because if you scroll
        # for some reason it isn't the true bottom. So we use an "almost"
        difference = abs(adj.get_value() - adj.get_upper())
        return difference < 1000

    def popin(self):
        """
        Popin back to the main window
        """

        try:
            assert self._popout_window
        except AttributeError:
            logging.warning('attempted popin even though not popped out')
            return

        self._popout_button_stack.set_visible_child(self._popout_button)

        self._popout_window.remove(self)
        self._popout_window.destroy()
        # If we don't then the popin detection and folding breaks
        del(self._popout_window)

        self.app.main_win.unconfigure_popout_window(self)
        self.is_poped = False

    def popout(self):
        """
        Popout the channel into a separate window
        """

        self.app.main_win.context_stack.remove(self)

        self.app.main_win.reconfigure_for_popout_window()

        self._popout_window = Handy.Window(
            default_width=600,
            default_height=400
        )
        self._popout_window.add(self)
        self._popout_window.present()
        self._popout_button_stack.set_visible_child(self._popin_button)
        self.is_poped = True

    def prepare_scroll_for_msg_send(self):
        """
        Schedule next message to cause screen to scroll
        """
        self._msg_sending_scrl_mode_en = True

    def unprepare_scroll_for_msg_send(self):
        """
        Disable mode of scheduling next messages to cause
        screen to scroll
        """
        self._msg_sending_scrl_mode_en = False

    @property
    def is_scroll_for_msg_send(self):
        """
        Wether currently the next received message is expected to be
        the one sent by the user, and it is expected that the view
        is scrolled to their message
        """
        return self._msg_sending_scrl_mode_en

    @Gtk.Template.Callback()
    def _on_popout_context_button_clicked(self, button):
        self.popout()

    @Gtk.Template.Callback()
    def on_popin_context_button_clicked(self, button):
        self.popin()

    @Gtk.Template.Callback()
    def _on_flap_toggle_button_clicked(self, button):
        self.app.main_win.main_flap.set_reveal_flap(
            not self.app.main_win.main_flap.get_reveal_flap()
        )

class MirdorphMessage(Gtk.ListBoxRow, EventReceiver):
    __gtype_name__ = "MirdorphMessage"

    def __init__(self, disc_message, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self._disc_message = disc_message

        # Overall unique identifier to tell duplicates apart
        # here it is a message id, however other ways are possible.
        # standard checking won't work because a message can have multiple
        # objects
        self.uniq_id = disc_message.id
        self.timestamp = disc_message.created_at.timestamp()

        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self._username_label = Gtk.Label(
            use_markup=True,
            # NOTE: a specific username can mess up the pango formatting
            label=f"<b>{disc_message.author.name}: </b>",
            xalign=0.0,
            vexpand=True,
            valign=Gtk.Align.START
        )
        self._message_label = Gtk.Label(label=disc_message.content, xalign=0.0, wrap=True)

        main_hbox.pack_start(self._username_label, False, False, 0)
        main_hbox.pack_start(self._message_label, True, True, 0)

        main_hbox.show_all()

        self.add(main_hbox)

class MessageView(Gtk.ScrolledWindow, EventReceiver):
    __gtype_name__ = "MessageView"

    def __init__(self, context, *args, **kwargs):
        Gtk.ListBox.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.set_policy(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC
        )

        self._message_listbox = Gtk.ListBox()
        # When nearly empty channel, messages should not pile up on top
        self._message_listbox.set_valign(Gtk.Align.END)

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

        self.add(self._message_listbox)

        self.context = context

    def _on_msg_send_mode_scl_send_wrap(self):
        self.context.scroll_messages_to_bottom()

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel_id:
            message_wid = MirdorphMessage(message)
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
            self.context.unprepare_scroll_for_msg_send()

    @property
    def history_loading_is_complete(self):
        """
        If history loading has completed atleast once

        This is useful for calling something that depends on history getting loaded,
        like scrolling the messages to the bottom. Not 100% accurate
        """
        # Works as the message listboxes are direct children of the message listbox
        # However not 100% accurate as some could have been from on_message,
        # but that is highly unlikely
        for child in self._message_listbox.get_children():
            if isinstance(child, MirdorphMessage):
                return True
        return False

    async def _get_history_messages_to_list(self, channel):
        """
        Return a list of Discord messages in current history,
        useful to call in other thread and use the list to build
        message objects
        """
        tmp_list = []
        # big limit temporary solution until we implement history reloading
        # on scroll
        async for message in channel.history(limit=1000):
            tmp_list.append(message)
        return tmp_list

    def _history_loading_gtk_target(self, messages: list):
        for message in messages:
            message_wid = MirdorphMessage(message)
            message_wid.show()

            # We need to check for duplicates and not add it if it is one
            # because load_history will often be called multiple times
            duplicate = False
            # The message listbox currently just has messages directly as children
            # so this work fine
            for already_existing_message in self._message_listbox.get_children():
                if (isinstance(already_existing_message, MirdorphMessage) and
                   message_wid.uniq_id == already_existing_message.uniq_id):
                    duplicate = True
                    break
            if not duplicate:
                self._message_listbox.add(message_wid)
            else:
                message_wid.destroy()
                del(message_wid)

        self._history_loading_spinner.stop()

        # This aquard thing needed because a listboxrow is automatically
        # inserted between the spinner and the listbox
        spin_row = self._history_loading_spinner.get_parent()
        spin_row.get_parent().remove(
            spin_row
        )
        spin_row.remove(self._history_loading_spinner)
        spin_row.destroy()
        del(spin_row)

        self._history_loading_spinner.destroy()
        del(self._history_loading_spinner)

    def _history_loading_target(self):
        messages = list(
            asyncio.run_coroutine_threadsafe(
                self._get_history_messages_to_list(
                    self.context.channel_disc
                ),
                Gio.Application.get_default().discord_loop
            ).result()
        )

        GLib.idle_add(self._history_loading_gtk_target, messages)

    def load_history(self):
        """
        Load the history of the view and it's channel

        You can only load once at a time, async operation
        """
        if self.context.is_loading_history:
            logging.warning("attempted to load history even if already loading")
            return
        self._history_loading_spinner = Gtk.Spinner()
        self._message_listbox.add(self._history_loading_spinner)
        self._history_loading_spinner.show()
        self._history_loading_spinner.start()
        message_loading_thread = threading.Thread(target=self._history_loading_target)
        message_loading_thread.start()


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message_entry_bar.ui')
class MessageEntryBar(Gtk.Box, EventReceiver):
    __gtype_name__ = "MessageEntryBar"

    def __init__(self, context, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.context = context
        # hacky global
        Gio.Application.get_default().bar_size_group.add_widget(self)
        self.app = Gio.Application.get_default()

    @Gtk.Template.Callback()
    def on_message_entry_activate(self, entry):
        message = entry.get_text()
        # Done here, not with a separate async wrapper with idle_add
        # because it doesn't help because if we do it from that
        # it executes in the wrong order.

        # Unsetting happens in on_message due to similar reasons
        self.context.prepare_scroll_for_msg_send()
        asyncio.run_coroutine_threadsafe(
            self.context.channel_disc.send(message),
            self.app.discord_loop
        )
        entry.set_text('')
        
