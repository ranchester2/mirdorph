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
import os
from pathlib import Path
from gi.repository import Gtk, Handy, Gio, GObject, GLib, Pango, GdkPixbuf
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui')
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    _channel_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, discord_channel: discord.abc.GuildChannel, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = discord_channel.id
        self.name = discord_channel.name
        self._channel_label.set_label('#' + discord_channel.name)

class MirdorphGuildEntry(Handy.ExpanderRow):
    __gtype_name__ = "MirdorphGuildEntry"

    _guild_icon_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    def __init__(self, guild_id, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)

        self._loading_state_spinner = Gtk.Spinner()
        self._loading_state_spinner.show()
        self.add_prefix(self._loading_state_spinner)
        self._loading_state_spinner.start()

        # For whatever reason it is needed
        self.set_hexpand(False)

        # Public because keeping track of which listbox is the current one is the job of the channel
        # sidebar, not the entry.
        self.channel_listbox = Gtk.ListBox()
        self.channel_listbox.show()
        self.channel_listbox.connect("row-activated", self._on_channel_list_entry_activated)

        self.add(self.channel_listbox)

        fetching_guild_thread = threading.Thread(
            target=self._fetching_guild_threaded_target,
            args=(guild_id,)
        )
        fetching_guild_thread.start()

    def do_search_display(self, search_string: str):
        row_match = None
        for channel_row in self.channel_listbox:
            if search_string.lower() in channel_row.name.lower():
                row_match = channel_row
                self.set_expanded(True)
                channel_row.get_style_context().add_class("channel-search-result")
                channel_row.get_style_context().remove_class("anti-channel-search-result")
            else:
                if row_match is not None:
                    channel_row.get_style_context().add_class("anti-channel-search-result")
                channel_row.get_style_context().remove_class("channel-search-result")

    def has_channel_search_result(self) -> bool:
        for channel_row in self.channel_listbox:
            if channel_row.get_style_context().has_class("channel-search-result"):
                return True
        return False

    def _get_icon_path_from_guild_id(self, guild_id) -> Path:
        return Path(self._guild_icon_dir_path / Path("icon" + "_" + str(guild_id) + ".png"))

    async def _get_guild_advanced_wrapper(self, client, guild_id):
        tmp_guild = await client.fetch_guild(guild_id)

        await asyncio.sleep(0.1)
        while client.get_guild(guild_id) is None:
            logging.info("couldnt get channel, sleeping for additional second")
            await asyncio.sleep(1)

        return client.get_guild(guild_id)

    async def _channel_is_private_to_you(self, self_member, channel):
        our_permissions = channel.permissions_for(self_member)
        return not our_permissions.view_channel

    async def _get_self_member(self, client):
        return await self._guild_disc.fetch_member(client.user.id)

    async def _save_guild_icon(self, asset):
        try:
            await asset.save(self._get_icon_path_from_guild_id(self._guild_disc.id))
        except discord.errors.DiscordException:
            logging.warning("guild does not have icon, not saving")

    def _fetching_guild_threaded_target(self, guild_id):
        self._guild_disc = asyncio.run_coroutine_threadsafe(
            self._get_guild_advanced_wrapper(
                Gio.Application.get_default().discord_client,
                guild_id
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        # So that we could query our permissions, not in loop for rate limit
        self_member = asyncio.run_coroutine_threadsafe(
            self._get_self_member(
                Gio.Application.get_default().discord_client
            ),
            Gio.Application.get_default().discord_loop
        ).result()
        self._private_guild_channel_ids = []
        for channel in self._guild_disc.channels:
            is_private = asyncio.run_coroutine_threadsafe(
                self._channel_is_private_to_you(
                    self_member,
                    channel
                ),
                Gio.Application.get_default().discord_loop
            ).result()
            if is_private:
                self._private_guild_channel_ids.append(channel.id)

        # They are saved in the cache path /
        # icon+guild_id+.png
        icon_asset = self._guild_disc.icon_url_as(size=4096, format="png")
        asyncio.run_coroutine_threadsafe(
            self._save_guild_icon(
                icon_asset
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        GLib.idle_add(self._build_guild_gtk_target)

    def _build_guild_gtk_target(self):
        self.set_title(self._guild_disc.name)
        # For filtering by search
        self.guild_name = self._guild_disc.name

        guild_image_path = self._get_icon_path_from_guild_id(self._guild_disc.id)
        if guild_image_path.is_file():
            guild_image = Handy.Avatar(size=32)
            def load_image(size, guild_image_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(guild_image_path),
                    width=size,
                    height=size,
                    preserve_aspect_ratio=False
                )
                return pixbuf
            guild_image.set_image_load_func(load_image, guild_image_path)
            guild_image.show()
            self.add_prefix(guild_image)
        else:
            guild_image = Handy.Avatar(size=32, show_initials=True)
            guild_image.set_text(self._guild_disc.name)
            guild_image.show()
            self.add_prefix(guild_image)

        for channel in self._guild_disc.channels:
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel)):
                continue

            if channel.id in self._private_guild_channel_ids:
                continue

            channel_entry = MirdorphChannelListEntry(channel)
            channel_entry.show()
            self.channel_listbox.add(channel_entry)

        self.remove(self._loading_state_spinner)

    def _on_channel_list_entry_activated(self, listbox, row):
        Gio.Application.get_default().main_win.show_active_channel(row.id)
        # Most mobile sidebar switching implementations work like this
        if Gio.Application.get_default().main_win.main_flap.get_folded():
            Gio.Application.get_default().main_win.main_flap.set_reveal_flap(False)

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box):
    __gtype_name__ = "MirdorphChannelSidebar"

    _view_switcher: Handy.ViewSwitcherBar = Gtk.Template.Child()
    _guild_list_search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    _guild_list_search_bar: Handy.SearchBar = Gtk.Template.Child()
    _channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    _channel_guild_loading_stack: Gtk.Stack = Gtk.Template.Child()
    _channel_guild_list_container: Gtk.Box = Gtk.Template.Child()
    _channel_guild_loading_spinner_page: Gtk.Spinner = Gtk.Template.Child()

    def __init__(self, channel_search_button: Gtk.ToggleButton, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        self._channel_guild_loading_stack.set_visible_child(self._channel_guild_loading_spinner_page)
        self._channel_search_button = channel_search_button

        self._guild_list_search_bar.connect_entry(self._guild_list_search_entry)
        self._channel_search_button.connect("notify::active", self._on_channel_search_button_toggled)

        build_guilds_thread = threading.Thread(target=self._build_guilds_target)
        build_guilds_thread.start()

    def _on_channel_search_button_toggled(self, button, param):
        self._guild_list_search_bar.set_search_mode(self._channel_search_button.get_active())

    @Gtk.Template.Callback()
    def _on_search_bar_search_enabled(self, search_bar, param):
        self._channel_search_button.set_active(self._guild_list_search_bar.get_search_mode())

    @Gtk.Template.Callback()
    def _on_guild_list_search_entry_changed(self, entry: Gtk.SearchEntry):
        def is_row_in_search_results(row: MirdorphGuildEntry, search_text: str) -> bool:
            try:
                row.guild_name
            except AttributeError:
                return True
            else:
                return search_text.lower() in row.guild_name.lower()

        search_string = self._guild_list_search_entry.get_text()
        focused_row = None

        [guild_row.do_search_display(search_string) for guild_row in self._channel_guild_list.get_children()]

        for guild_row in self._channel_guild_list.get_children():
            if is_row_in_search_results(guild_row, search_string):
                guild_row.set_visible(True)
            else:
                guild_row.set_visible(guild_row.has_channel_search_result())

            if focused_row is None and is_row_in_search_results(guild_row, search_string):
                for row in self._channel_guild_list.get_children():
                    row.set_expanded(False)
                focused_row = guild_row
                guild_row.set_expanded(True)

    async def _get_guild_ids_list(self, client):
        # Why the waiting?
        # We can't get guilds with all the feauters with fetching
        # So we wait here for the cache to get built up so that we
        # could get guild objects
        await asyncio.sleep(0.25)
        while not client.guilds:
            logging.info("couldnt get list, sleeping for additional quarter second")
            await asyncio.sleep(0.25)

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
            # Why? Because it is hard to access the listox manager from the event
            # in the guild_entry itself
            guild_entry.channel_listbox.connect("row-activated", self._on_guild_entry_channel_list_activate)
            guild_entry.show()
            self._channel_guild_list.add(guild_entry)
        self._channel_guild_loading_stack.set_visible_child(self._channel_guild_list_container)

    def _on_guild_entry_channel_list_activate(self, listbox, row):
        self.set_listbox_active(listbox)

    def set_listbox_active(self, active_listbox: Gtk.ListBox):
        """
        Set which listbox is the currently selected one, to unselect
        all other remaining listboxes.

        param:
            active_listbox, the one that should be the only one, usually self
        """
        for listbox in [x.channel_listbox for x in self._channel_guild_list.get_children()]:
            if listbox == active_listbox:
                continue
            else:
                listbox.set_selection_mode(Gtk.SelectionMode.NONE)
                listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

