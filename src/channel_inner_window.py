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
from gi.repository import Gtk, Handy, Gio
from .event_receiver import EventReceiver


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_inner_window.ui')
class ChannelInnerWindow(Gtk.Box, EventReceiver):
    __gtype_name__ = "ChannelInnerWindow"

    toplevel_empty_stack: Gtk.Stack = Gtk.Template.Child()
    empty_status_page: Handy.StatusPage = Gtk.Template.Child()

    content_box: Gtk.Box = Gtk.Template.Child()

    popout_button_stack: Gtk.Stack = Gtk.Template.Child()
    popout_button: Gtk.Button = Gtk.Template.Child()
    popin_button: Gtk.Button = Gtk.Template.Child()

    flap_toggle_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel=None, empty=True, *args, **kwargs):
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

            self.message_view = MessageView(context=self)
            self.message_view.show()
            self.content_box.pack_start(self.message_view, True, True, 0)

            self.message_entry_bar = MessageEntryBar(context=self)
            self.message_entry_bar.show()
            self.content_box.pack_end(self.message_entry_bar, False, False, 0)
            self.content_box.pack_end(Gtk.Separator(visible=True), False, False, 0)
        elif self.empty:
            self.popout_button.destroy()
            self.popin_button.destroy()
            self.popout_button_stack.destroy()
            self.toplevel_empty_stack.set_visible_child(self.empty_status_page)

    # This is connected in main's handle context
    def handle_flap_folding(self, flap, folded):
        if flap.get_folded():
            self.flap_toggle_button.set_visible(True)
            self.popout_button_stack.set_visible(False)
            flap.set_swipe_to_close(True)

            self.popin()
        else:
            self.flap_toggle_button.set_visible(False)
            self.popout_button_stack.set_visible(True)
            flap.set_swipe_to_close(False)

    def popin(self):
        try:
            assert self.popout_window
        except AttributeError:
            logging.warning('attempted popin even though not popped out')
            return

        self.popout_button_stack.set_visible_child(self.popout_button)

        self.popout_window.remove(self)
        self.popout_window.destroy()

        self.app.main_win.unconfigure_popout_window(self)
        self.is_poped = False

    def popout(self):
        self.app.main_win.context_stack.remove(self)

        self.app.main_win.reconfigure_for_popout_window()

        self.popout_window = Handy.Window(
            default_width=600,
            default_height=400
        )
        self.popout_window.add(self)
        self.popout_window.present()
        self.popout_button_stack.set_visible_child(self.popin_button)
        self.is_poped = True

    @Gtk.Template.Callback()
    def on_popout_context_button_clicked(self, button):
        self.popout()

    @Gtk.Template.Callback()
    def on_popin_context_button_clicked(self, button):
        self.popin()

    @Gtk.Template.Callback()
    def on_flap_toggle_button_clicked(self, button):
        self.app.main_win.main_flap.set_reveal_flap(
            not self.app.main_win.main_flap.get_reveal_flap()
        )


class MessageView(Gtk.ScrolledWindow, EventReceiver):
    __gtype_name__ = "MessageView"

    def __init__(self, context, *args, **kwargs):
        Gtk.ListBox.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.message_listbox = Gtk.ListBox()
        self.message_listbox.show()

        self.add(self.message_listbox)

        self.context = context

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel_id:
            message_row = Gtk.ListBoxRow()
            message_row.add(Gtk.Label(label=message.content, xalign=0.0))
            message_row.show_all()
            self.message_listbox.add(message_row)

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
        asyncio.run_coroutine_threadsafe(
            self.context.channel_disc.send(message),
            self.app.discord_loop
        )
        entry.set_text('')
        
