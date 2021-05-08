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
import threading
import logging
from gi.repository import Gtk, Handy, Gio
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui')
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    _channel_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = context.channel_id
        self._channel_label.set_label('#' + context.channel_disc.name)

class MirdorphGuildEntry(Handy.ExpanderRow):
    __gtype_name__ = "MirdorphGuildEntry"

    def __init__(self, guild_id, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs):

        # Initially its just a spinner until we load everything
        self._loading_state_spinner = Gtk.Spinner()
        self._loading_state_spinner.show()
        self.add_prefix(self._loading_state_spinner)
        self._loading_state_spinner.start()

        fetching_guild_thread = threading.Thread(
            target=self._fetching_guild_threaded_target,
            args=(guild_id,)
        )


    def _fetching_guild_threaded_target(self, guild_id):
        self._guild_disc = asyncio.run_coroutine_threadsafe(
            Gio.Application.get_default().discord_client.fetch_guild(guild_id),
            Gio.Application.get_default().discord_loop
        ).result()

        GLib.idle_add(self._build_guild_gtk_target)

    def _build_guild_gtk_target(self):
        self.remove(self._loading_state_spinner)
        self.set_title(self._guild_disc.name)


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box, EventReceiver):
    __gtype_name__ = "MirdorphChannelSidebar"

    _view_switcher: Handy.ViewSwitcherBar = Gtk.Template.Child()
    _channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        # Temp, we could use containe.get_children too
        # However the guild list will need a complete
        # redesign when we implement it as in mockup
        # and give it the required functionality
        self._list_entries = [
        ]

        # hacky global
        Gio.Application.get_default().bar_size_group.add_widget(self._view_switcher)

    def add_channel(self, context):
        """
        Forcibly add a channel

        NOTE: it is not recommended to use this,
        instead create a context and use `inform_of_new_channel`

        param:
            context - the context of the channel you want to add
        """

        list_entry = MirdorphChannelListEntry(context)
        list_entry.show()
        self._list_entries.append(list_entry)
        self._channel_guild_list.add(list_entry)

    def inform_of_new_channel(self):
        """
        Check for channels and rebuild the sidebar
        if needed
        """

        # This is to simply inform of when a new chaannel is added
        # so that we could react accordingly.
        # Which is why we need to destroy all currently added ones
        # to avoid duplicates
        for entry in self._list_entries:
            self._list_entries.remove(entry)
            entry.get_parent().remove(entry)
            entry.destroy()
            del(entry)

        for channel in Gio.Application.get_default().currently_running_channels:
            context = Gio.Application.get_default().retrieve_inner_window_context(channel)
            self.add_channel(context)

        # Check for dupes, because for whatever reason they happen
        found_ids = []
        for entry in self._list_entries:
            if entry.id in found_ids:
                logging.warning("channel sidebar: DUPE FOUND")
                self._list_entries.remove(entry)
                entry.get_parent().remove(entry)
                entry.destroy()
                continue

            found_ids.append(entry.id)

    @Gtk.Template.Callback()
    def _on_guild_list_entry_selected(self, listbox, row):
        Gio.Application.get_default().main_win.show_active_channel(row.id)
