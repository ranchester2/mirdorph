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
from gi.repository import Gtk, Handy, Gio
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui')
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    channel_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = context.channel_id
        self.channel_label.set_label('#' + context.channel_disc.name)

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box, EventReceiver):
    __gtype_name__ = "MirdorphChannelSidebar"

    view_switcher: Handy.ViewSwitcherBar = Gtk.Template.Child()
    channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.list_entries = [
        ]

        # hacky global
        Gio.Application.get_default().bar_size_group.add_widget(self.view_switcher)

    def add_channel(self, context):
        list_entry = MirdorphChannelListEntry(context)
        list_entry.show()
        self.list_entries.append(list_entry)
        self.channel_guild_list.add(list_entry)

    def inform_of_new_channel(self):
        # This is to simply inform of when a new chaannel is added
        # so that we could react accordingly.
        # Which is why we need to destroy all currently added ones
        # to avoid duplicates

        for entry in self.list_entries:
            self.list_entries.remove(entry)
            entry.get_parent().remove(entry)
            entry.destroy()

        for channel in Gio.Application.get_default().currently_running_channels:
            context = Gio.Application.get_default().retrieve_inner_window_context(channel)
            self.add_channel(context)

    @Gtk.Template.Callback()
    def on_guild_list_entry_selected(self, listbox, row):
        Gio.Application.get_default().main_win.show_active_channel(row.id)
