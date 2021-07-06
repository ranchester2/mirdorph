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
import time
from pathlib import Path
from gi.repository import Adw, Gtk, Gio, GObject, GLib, GdkPixbuf

# Use this to filter out only text channels, which we support
TEXT_CHANNEL_FILTER = (discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel)

def separator_listbox_header_func(row, before):
    if before is None:
        row.set_header(None)
        return
    current = row.get_header()
    if current is None:
        current = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        row.set_header(current)


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_list_entry.ui")
class MirdorphChannelListEntry(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphChannelListEntry"

    _channel_label: Gtk.Label = Gtk.Template.Child()
    _search_context_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, discord_channel: discord.abc.GuildChannel, search_mode=False, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.id = discord_channel.id
        self.name = discord_channel.name
        self._channel_label.set_label("#" + self.name)

        if search_mode:
            context_text = discord_channel.guild.name
            if discord_channel.category:
                context_text += f" -> {discord_channel.category.name}"
            self._search_context_label.set_label(context_text)

class MirdorphGuildEntry(Adw.ExpanderRow):
    __gtype_name__ = "MirdorphGuildEntry"

    _guild_icon_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    def __init__(self, disc_guild: discord.Guild, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._disc_guild = disc_guild
        self.set_title(self._disc_guild.name)

        self._loading_state_spinner = Gtk.Spinner()
        self.add_prefix(self._loading_state_spinner)
        self._loading_state_spinner.start()

        # Channel sidebar should always take up the smallest amount of
        # horizontal space.
        self.set_hexpand(False)

        # Public as the listbox is an extension of the sidebar, the sidebar
        # should keep track of witch is selected for example, and the sidebar
        # connects and handles row activations
        self.channel_listbox = Gtk.ListBox()
        self.channel_listbox.set_header_func(separator_listbox_header_func)
        self.add(self.channel_listbox)

        threading.Thread(
            target=self._fetching_guild_threaded_target
        ).start()

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
        guild_avatar = Adw.Avatar(size=32, show_initials=True)
        guild_avatar.set_text(self._disc_guild.name)

        if guild_image_path.is_file():
            guild_avatar = Adw.Avatar(size=32)
            image_wid = Gtk.Image.new_from_file(
                str(guild_image_path)
            )
            guild_avatar.set_custom_image(image_wid.get_paintable())
            self.add_prefix(guild_avatar)

        self.add_prefix(guild_avatar)

        for channel in self._disc_guild.channels:
            if isinstance(channel, TEXT_CHANNEL_FILTER):
                continue

            if not channel.permissions_for(self._disc_guild.me).view_channel:
                continue

            channel_entry = MirdorphChannelListEntry(channel)
            self.channel_listbox.append(channel_entry)

        self.remove(self._loading_state_spinner)

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_sidebar.ui')
class MirdorphChannelSidebar(Gtk.Box):
    __gtype_name__ = "MirdorphChannelSidebar"

    _guild_list_search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    _guild_list_search_bar: Gtk.SearchBar = Gtk.Template.Child()
    _channel_guild_list: Gtk.ListBox = Gtk.Template.Child()

    _channel_guild_loading_stack: Gtk.Stack = Gtk.Template.Child()
    _channel_guild_list_container: Gtk.Box = Gtk.Template.Child()
    _guild_loading_page: Gtk.Spinner = Gtk.Template.Child()

    _search_list: Gtk.ListBox = Gtk.Template.Child()
    _search_mode_stack: Gtk.Stack = Gtk.Template.Child()
    _search_empty_state_stack: Gtk.Stack = Gtk.Template.Child()

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
        self.app.set_accels_for_action("app.search-guilds", ["<Control>k"])

        self._guild_list_search_bar.connect_entry(self._guild_list_search_entry)
        self._search_list.set_header_func(separator_listbox_header_func)

        threading.Thread(target=self._build_guilds_target).start()

    def _select_default_search_row(self):
        """
        Selects the row that is currently the top search result
        """
        for row in self._search_list:
            if self._search_filter_func(row, self._guild_list_search_entry.get_text()):
                self._search_list.select_row(row)
                return

    def _search_filter_func(self, row: MirdorphChannelListEntry, search_string: str):
        return search_string.lower() in "#" + row.name.lower()

    @Gtk.Template.Callback()
    def _on_search_changed(self, search_entry: Gtk.SearchEntry):
        if self._guild_list_search_entry.get_text():
            self._search_list.invalidate_filter()
            self._search_mode_stack.set_visible_child_name("search")
            self._search_list.set_filter_func(self._search_filter_func, self._guild_list_search_entry.get_text())

            any_result_found = False
            # There is no way to check if a row is currently filtered out,
            # however we can run the fitler_func manually, and we know the user_data
            # is the current text of the search entry.
            for row in self._search_list:
                if self._search_filter_func(row, self._guild_list_search_entry.get_text()):
                    any_result_found = True

            # No results
            if not any_result_found:
                self._search_empty_state_stack.set_visible_child_name("empty")
            else:
                self._search_empty_state_stack.set_visible_child_name("results")
                # By default immediately select the first search result, which is what is selected
                # if you hit enter too.
                self._select_default_search_row()
        else:
            self._search_mode_stack.set_visible_child_name("content")

    @Gtk.Template.Callback()
    def _on_search_activate(self, search_entry: Gtk.SearchEntry):
        # It doesn't make sense to activate the last valid search if no search results
        # are found.
        if self._search_empty_state_stack.get_visible_child_name() == "results":
            self._guild_list_search_bar.set_search_mode(False)
            self._set_channel_entry_active(self._search_list.get_selected_row())

    def _get_guilds_list(self) -> list:
        """
        Helper function to get the guilds list while handling client not
        yet being connected.

        The channel sidebar is created at startup, and .guilds doesn't work
        if the client isn't fully connected yet.

        Must be called in separate thread (blocking if not connected).
        """
        while not self.app.discord_client.guilds:
            time.sleep(0.25)

        return self.app.discord_client.guilds

    def _build_guilds_target(self):
        guilds = self._get_guilds_list()

        GLib.idle_add(self._build_guilds_gtk_target, guilds)

    def _build_guilds_gtk_target(self, guilds: list):
        for guild in guilds:
            guild_entry = MirdorphGuildEntry(guild)
            guild_entry.channel_listbox.connect("row-activated", self._on_channel_entry_activated)
            self._channel_guild_list.append(guild_entry)

            # NOTE: may be a bit bad to performance to have such a massive listbox when not even needed,
            # maybe better to build it on search and destroy it on search end?
            for channel in guild.channels:
                if not isinstance(channel, TEXT_CHANNEL_FILTER) and channel.permissions_for(guild.me).view_channel:
                    search_channel_entry = MirdorphChannelListEntry(channel, search_mode=True)
                    self._search_list.append(search_channel_entry)

        self._channel_guild_loading_stack.set_visible_child(self._channel_guild_list_container)

    @Gtk.Template.Callback()
    def _on_channel_entry_activated(self, listbox: Gtk.ListBox, row: MirdorphChannelListEntry):
        if self._guild_list_search_bar.get_search_mode():
            self._guild_list_search_bar.set_search_mode(False)
        self._set_channel_entry_active(row)

    def _set_channel_entry_active(self, activation_row: MirdorphChannelListEntry):
        """
        Correctly mark the row as active, and do selection of it (IE opening it).
        This correctly hadnles search list logic, unselecting other listboxes
        and similar.

        param:
            activation_row, the MirdorphChannelListEntry you want to mark as active
        """
        active_listbox = None
        for guild_entry in self._channel_guild_list:
            for row in guild_entry.channel_listbox:
                # The id matters, not the specific instance, especially with search
                if row.id == activation_row.id:
                    guild_entry.channel_listbox.select_row(row)
                    guild_entry.set_expanded(True)
                    active_listbox = guild_entry.channel_listbox
            if guild_entry.channel_listbox != active_listbox:
                guild_entry.channel_listbox.unselect_all()

        self.app.main_win.show_active_channel(activation_row.id)

        # Most mobile sidebar switching implementations work like this
        if self.app.main_win.main_flap.get_folded():
            self.app.main_win.main_flap.set_reveal_flap(False)
