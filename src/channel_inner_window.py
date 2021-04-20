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

from gi.repository import Gtk, Handy, Gio
from .event_receiver import EventReceiver


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_inner_window.ui')
class ChannelInnerWindow(Gtk.Box, EventReceiver):
    __gtype_name__ = "ChannelInnerWindow"

    toplevel_empty_stack: Gtk.Stack = Gtk.Template.Child()
    empty_status_page: Handy.StatusPage = Gtk.Template.Child()

    scrolled_window: Gtk.ScrolledWindow = Gtk.Template.Child()

    popout_button_stack: Gtk.Stack = Gtk.Template.Child()
    popout_button: Gtk.Button = Gtk.Template.Child()
    popin_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel=None, empty=True, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self.channel = channel
        self.empty = empty
        if self.channel is None:
            self.empty = True

        if not self.empty:
            self.message_view = MessageView(context=self)
            self.message_view.show()
            self.scrolled_window.add(self.message_view)
        elif self.empty:
            self.popout_button.destroy()
            self.popin_button.destroy()
            self.popout_button_stack.destroy()
            self.toplevel_empty_stack.set_visible_child(self.empty_status_page)

    @Gtk.Template.Callback()
    def on_popout_context_button_clicked(self, button):
        flap = self.get_parent()
        flap.remove(self)

        og_win_main: Handy.ApplicationWindow = Gio.Application.get_default().main_win
        og_win_main.reconfigure_for_popout_window()

        self.popout_window = Handy.Window(
            default_width=400,
            default_height=290
        )
        self.popout_window.add(self)
        self.popout_window.present()
        self.popout_button_stack.set_visible_child(self.popin_button)

    @Gtk.Template.Callback()
    def on_popin_context_button_clicked(self, button):
        og_win_main = Gio.Application.get_default().main_win

        self.popout_button_stack.set_visible_child(self.popout_button)

        self.popout_window.remove(self)
        self.popout_window.destroy()

        og_win_main.unconfigure_for_popout_window()

        og_win_main.main_flap.set_content(self)


class MessageView(Gtk.ListBox, EventReceiver):
    __gtype_name__ = "MessageView"

    def __init__(self, context, *args, **kwargs):
        Gtk.ListBox.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.context = context

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel:
            message_row = Gtk.ListBoxRow()
            message_row.add(Gtk.Label(label=message.content, xalign=0.0))
            message_row.show_all()
            self.add(message_row)
