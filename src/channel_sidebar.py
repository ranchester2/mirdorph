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
import discord
from gi.repository import Gtk, Handy, Gio, GLib, Pango
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui')
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    _channel_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, discord_channel: discord.abc.GuildChannel, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = discord_channel.id
        self._channel_label.set_label('#' + discord_channel.name)

class MirdorphGuildEntry(Handy.ExpanderRow):
    __gtype_name__ = "MirdorphGuildEntry"

    def __init__(self, guild_id, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)

        # Initially its just a spinner until we load everything
        self._loading_state_spinner = Gtk.Spinner()
        self._loading_state_spinner.show()
        self.add_prefix(self._loading_state_spinner)
        self._loading_state_spinner.start()

        # For whatever reason it is needed
        self.set_hexpand(False)

        fetching_guild_thread = threading.Thread(
            target=self._fetching_guild_threaded_target,
            args=(guild_id,)
        )
        fetching_guild_thread.start()

    async def _get_guild_advanced_wrapper(self, client, guild_id):
        tmp_guild = await client.fetch_guild(guild_id)

        await asyncio.sleep(0.1)
        while client.get_guild(guild_id) is None:
            logging.info("couldnt get channel, sleeping for additional second")
            await asyncio.sleep(1)

        return client.get_guild(guild_id)

    def _fetching_guild_threaded_target(self, guild_id):
        self._guild_disc = asyncio.run_coroutine_threadsafe(
            self._get_guild_advanced_wrapper(
                Gio.Application.get_default().discord_client,
                guild_id
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        GLib.idle_add(self._build_guild_gtk_target)

    def _build_guild_gtk_target(self):
        self.set_title(self._guild_disc.name)

        self._channel_listbox = Gtk.ListBox()
        self._channel_listbox.show()
        self._channel_listbox.connect("row-activated", self._on_channel_list_entry_activated)

        self.add(self._channel_listbox)

        for channel in self._guild_disc.channels:
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel)):
                continue
            channel_entry = MirdorphChannelListEntry(channel)
            channel_entry.show()
            self._channel_listbox.add(channel_entry)

        self.remove(self._loading_state_spinner)

    def _on_channel_list_entry_activated(self, listbox, row):
        Gio.Application.get_default().main_win.show_active_channel(row.id)

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box, EventReceiver):
    __gtype_name__ = "MirdorphChannelSidebar"

    _view_switcher: Handy.ViewSwitcherBar = Gtk.Template.Child()
    _channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    _channel_guild_loading_stack: Gtk.Stack = Gtk.Template.Child()
    _channel_guild_list_scrolled_win: Gtk.ScrolledWindow = Gtk.Template.Child()
    _channel_guild_loading_spinner_page: Gtk.Spinner = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        # hacky global
        Gio.Application.get_default().bar_size_group.add_widget(self._view_switcher)

        self._channel_guild_loading_stack.set_visible_child(self._channel_guild_loading_spinner_page)
        build_guilds_thread = threading.Thread(target=self._build_guilds_target)
        build_guilds_thread.start()

    async def _get_guild_ids_list(self, client):
        # Why the waiting?
        # We can't get guilds with all the feauters with fetching
        # So we wait here for the cache to get built up so that we
        # could get guild objects
        await asyncio.sleep(1)
        while not client.guilds:
            logging.info("couldnt get list, sleeping for additional second")
            await asyncio.sleep(1)

        guild_ids_list = [guild.id for guild in client.guilds]
        return guild_ids_list

    def _build_guilds_target(self):
        guild_ids = asyncio.run_coroutine_threadsafe(
            self._get_guild_ids_list(
                Gio.Application.get_default().discord_client
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        GLib.idle_add(self._build_guilds_gtk_target, guild_ids)

    def _build_guilds_gtk_target(self, guild_ids):
        for guild_id in guild_ids:
            guild_entry = MirdorphGuildEntry(guild_id)
            guild_entry.show()
            self._channel_guild_list.add(guild_entry)
        self._channel_guild_loading_stack.set_visible_child(self._channel_guild_list_scrolled_win)

