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
from gi.repository import Gtk, Gio, GObject, GLib, GdkPixbuf, Handy
from .event_receiver import EventReceiver

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui")
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    _channel_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, discord_channel: discord.abc.GuildChannel, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = discord_channel.id
        self.name = discord_channel.name
        self._channel_label.set_label("#" + discord_channel.name)

class MirdorphGuildEntry(Handy.ExpanderRow):
    __gtype_name__ = "MirdorphGuildEntry"

    _guild_icon_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    def __init__(self, disc_guild: discord.Guild, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._disc_guild = disc_guild
        self.set_title(self._disc_guild.name)
        # For filtering by search
        self.guild_name = self._disc_guild.name

        self._loading_state_spinner = Gtk.Spinner()
        self._loading_state_spinner.show()
        self.add_prefix(self._loading_state_spinner)
        self._loading_state_spinner.start()

        # Channel sidebar should always take up the smallest amount of
        # horizontal space.
        self.set_hexpand(False)

        # Public because keeping track of which listbox is the current one is the job of the channel
        # sidebar, not the entry.
        self.channel_listbox = Gtk.ListBox()
        self.channel_listbox.show()
        # Nice separators between rows
        def channel_listbox_header_func(row, before):
            if before is None:
                row.set_header(None)
                return
            current = row.get_header()
            if current is None:
                current = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
                current.show()
                row.set_header(current)
        self.channel_listbox.set_header_func(channel_listbox_header_func)
        self.channel_listbox.connect("row-activated", self._on_channel_list_entry_activated)
        self.add(self.channel_listbox)

        threading.Thread(
            target=self._fetching_guild_threaded_target
        ).start()

    def do_search_display(self, search_string: str) -> MirdorphChannelListEntry:
        """
        Do search in the guild's itself's list of channels based on the search string

        param:
            search_string: `str` of what is being searched for
        returns:
            `MirdorphChannelListEntry` of the first match if a search was found at all,
            `None` if no viable row was found
        """
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
        return row_match

    def has_channel_search_result(self) -> bool:
        for channel_row in self.channel_listbox:
            if channel_row.get_style_context().has_class("channel-search-result"):
                return True
        return False

    @staticmethod
    def _get_icon_path_from_guild_id(guild_id: int) -> Path:
        return Path(
            MirdorphGuildEntry._guild_icon_dir_path / Path("icon" + "_" + str(guild_id) + ".png")
        )

    async def _save_guild_icon(self, asset):
        try:
            await asset.save(self._get_icon_path_from_guild_id(self._disc_guild.id))
        except discord.errors.DiscordException:
            logging.warning("guild does not have icon, not saving")

    def _fetching_guild_threaded_target(self):
        # Originally this was also for the guild itself, however now
        # just for the image
        icon_asset = self._disc_guild.icon_url_as(size=4096, format="png")
        asyncio.run_coroutine_threadsafe(
            self._save_guild_icon(
                icon_asset
            ),
            self.app.discord_loop
        ).result()

        GLib.idle_add(self._build_guild_gtk_target)

    def _build_guild_gtk_target(self):
        guild_image_path = self._get_icon_path_from_guild_id(self._disc_guild.id)
        if guild_image_path.is_file():
            guild_image = Handy.Avatar(size=32)
            def load_image(size, guild_image_path: Path):
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
        # The image isn't downloaded if the guild doesn't have one
        else:
            guild_image = Handy.Avatar(size=32, show_initials=True)
            guild_image.set_text(self._disc_guild.name)
            guild_image.show()
            self.add_prefix(guild_image)

        for channel in self._disc_guild.channels:
            # These channels aren't supported yet
            if isinstance(channel, (discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel)):
                continue

            if not channel.permissions_for(self._disc_guild.me).view_channel:
                continue

            channel_entry = MirdorphChannelListEntry(channel)
            channel_entry.show()
            self.channel_listbox.add(channel_entry)

        self.remove(self._loading_state_spinner)

    def _on_channel_list_entry_activated(self, listbox, row):
        self.app.main_win.show_active_channel(row.id)
        # Most mobile sidebar switching implementations work like this
        if self.app.main_win.main_flap.get_folded():
            self.app.main_win.main_flap.set_reveal_flap(False)

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box):
    __gtype_name__ = "MirdorphChannelSidebar"

    _guild_list_search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    _guild_list_search_bar: Handy.SearchBar = Gtk.Template.Child()
    _channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    _channel_guild_loading_stack: Gtk.Stack = Gtk.Template.Child()
    _channel_guild_list_container: Gtk.Box = Gtk.Template.Child()
    _guild_loading_page: Gtk.Spinner = Gtk.Template.Child()

    def __init__(self, channel_search_button: Gtk.ToggleButton, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._channel_guild_loading_stack.set_visible_child(self._guild_loading_page)
        self._channel_search_button = channel_search_button

        self._channel_search_button.bind_property(
            "active",
            self._guild_list_search_bar,
            "search-mode-enabled",
            GObject.BindingFlags.BIDIRECTIONAL
        )
        search_action = Gio.PropertyAction.new("search-guilds", self._guild_list_search_bar, "search-mode-enabled")
        self.app.add_action(search_action)
        self.app.set_accels_for_action("app.search-guilds", ["<Primary>k"])

        self._guild_list_search_bar.connect_entry(self._guild_list_search_entry)

        # For search, the channel that with the sum of indicators is the one that is
        # the most likely search result.
        self._most_wanted_search_channel = None

        threading.Thread(target=self._build_guilds_target).start()

    @Gtk.Template.Callback()
    def _on_guild_list_search_entry_changed(self, entry: Gtk.SearchEntry):
        self._most_wanted_search_channel = None

        # Clean Up when search is closed
        if not self._guild_list_search_entry.get_text():
            for guild_row in self._channel_guild_list.get_children():
                guild_row.set_visible(True)
            for channel_listbox in [guild_row.channel_listbox for guild_row in self._channel_guild_list.get_children()]:
                for channel_row in channel_listbox.get_children():
                    channel_row.get_style_context().remove_class("channel-search-result")
                    channel_row.get_style_context().remove_class("anti-channel-search-result")
            return

        def is_row_in_search_results(row: MirdorphGuildEntry, search_text: str) -> bool:
            try:
                row.guild_name
            except AttributeError:
                return True
            else:
                return search_text.lower() in row.guild_name.lower()

        search_string = self._guild_list_search_entry.get_text()
        focused_row = None

        already_selected_most_wanted_find_attempt = False
        for guild_row in self._channel_guild_list.get_children():
            find_attempt = guild_row.do_search_display(search_string)
            if find_attempt is not None and not already_selected_most_wanted_find_attempt:
                already_selected_most_wanted_find_attempt = True
                self._most_wanted_search_channel = find_attempt

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

    @Gtk.Template.Callback()
    def _on_guild_list_search_entry_activate(self, entry: Gtk.SearchEntry):
        if self._most_wanted_search_channel:
            self._most_wanted_search_channel.emit("activate")
            self._guild_list_search_bar.set_search_mode(False)

    async def _get_guilds_list(self) -> list:
        # Why the waiting?
        # This is often loaded before our client is fully connected.
        # This also then serves as the entire application's "loading" state.
        # TODO: I might think about having a separate toplevel loading page for the app
        # in the future.
        while not self.app.discord_client.guilds:
            logging.info("guilds not synced, sleeping for additional quarter second")
            await asyncio.sleep(0.25)

        return self.app.discord_client.guilds

    def _build_guilds_target(self):
        guilds = asyncio.run_coroutine_threadsafe(
            self._get_guilds_list(),
            self.app.discord_loop
        ).result()

        GLib.idle_add(self._build_guilds_gtk_target, guilds)

    def _build_guilds_gtk_target(self, guilds: list):
        for guild in guilds:
            guild_entry = MirdorphGuildEntry(guild)
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
                # By search we might select a listbox which isn't currently expanded
                for guild_row in self._channel_guild_list:
                    if guild_row.channel_listbox == active_listbox:
                        guild_row.set_expanded(True)
            else:
                # Setting to none and back removes the selection
                listbox.set_selection_mode(Gtk.SelectionMode.NONE)
                listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)

