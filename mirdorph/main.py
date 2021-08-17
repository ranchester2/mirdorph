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

import sys
import logging
import os
import shutil
import keyring
import asyncio
import discord.ext.commands
from gi.repository import Adw, Gtk, Gdk, GLib, Gio
from pathlib import Path
from .login_window import MirdorphLoginWindow
from .main_window import MirdorphMainWindow
from .event_manager import EventManager
from .channel_inner_window import ChannelInnerWindow
from .settings_window import MirdorphSettingsWindow
from .confman import ConfManager
from .plugin import MrdPluginEngine, MrdExtensionSet, MrdApplicationPlugin


class Application(Gtk.Application):

    def __init__(self, discord_loop, discord_client, keyring_exists=False):
        super().__init__(application_id="org.gnome.gitlab.ranchester.Mirdorph",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Mirdorph")
        GLib.set_prgname("org.gnome.gitlab.ranchester.Mirdorph")
        self.discord_loop: asyncio.BaseEventLoop = discord_loop
        self.discord_client: discord.ext.commands.Bot = discord_client
        self.keyring_exists = keyring_exists

        self.confman = ConfManager()
        self.event_manager = EventManager()
        self.plugin_engine = MrdPluginEngine()

        self._inner_window_contexts = {}

        # Why the custom member cache? Doesn't discord.py have one?
        # Yes, however it usually doesn't actually work, which leads to doing
        # a billion calls for getting a member from a guild to get the username
        # color for the author of a message. We can optimise quite a lot by
        # implementing this custom cache.
        self.custom_member_cache = {}

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Adw.init()
        # Better to do this here as extensions can have the running lifetime of
        # the entire application
        for plugin in self.plugin_engine.get_available_plugins():
            plugin.connect("notify::active", self._sync_enabled_plugins_with_conf)

        [
            self.plugin_engine.load_plugin(
                self.plugin_engine.get_plugin_from_module(module_name)
            )
            for module_name in self.confman.get_value("enabled_extensions")
        ]

        self._extension_set = MrdExtensionSet(
            self.plugin_engine,
            MrdApplicationPlugin
        )
        for plugin in self._extension_set:
            plugin.u_activatable.load()
        self._extension_set.connect("extension_added", lambda set, plugin : plugin.u_activatable.load())
        self._extension_set.connect("extension_removed", lambda set, plugin : plugin.u_activatable.unload())

        # These are only the extremely "global" actions,
        # where it is significantly more convenient, the widget
        # itself adds the action (for example channel sidebar search)
        actions = [
            {
                "name": "settings",
                "func": self.show_settings_window,
                "accel": "<Control>comma"
            },
            {
                "name": "about",
                "func": self.show_about_dialog
            },
            {
                "name": "logout",
                "func": self.log_out
            }
        ]

        for a in actions:
            c_action = Gio.SimpleAction.new(a["name"], None)
            c_action.connect("activate", a["func"])
            self.add_action(c_action)
            if "accel" in a.keys():
                self.set_accels_for_action(
                    f"app.{a['name']}",
                    [a["accel"]]
                )

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_resource(
            "/org/gnome/gitlab/ranchester/Mirdorph/ui/gtk_style.css"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        logging.info("clearing cache")
        cache_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))
        cache_dir_path.mkdir(exist_ok=True)
        shutil.rmtree(cache_dir_path)
        cache_dir_path.mkdir(parents=True, exist_ok=True)

        if self.keyring_exists:
            logging.info("launching with token")
            # A lot of things break with multiple main windows,
            # while this still creats multiple discord clients,
            # it prevents further damage.
            # The underlying issue why we can't handle this nicely
            # is because discord is started before this. And if
            # the application already exists, the process changes,
            # so we can't kill it easily.
            if self.props.active_window:
                logging.fatal("Multiple Window formation error")
                os._exit(1)
            self.main_win = MirdorphMainWindow(application=self)
            self.main_win.present()
        else:
            logging.info("launching token retrieval sequence")
            win = self.props.active_window
            if not win:
                win = MirdorphLoginWindow(application=self)
            win.present()

    def do_shutdown(self, *args):
        for plugin in self.plugin_engine.get_enabled_plugins():
            # We don't want to empty the enabled plugin conf here
            plugin.disconnect_by_func(self._sync_enabled_plugins_with_conf)
            self.plugin_engine.unload_plugin(plugin)
        # Dangerous, but we need to kill the discord thread for now
        os._exit(0)

    def _sync_enabled_plugins_with_conf(self, *args):
        """
        Sync the list of currently enabled plugins to confman
        so that they can be re-enabled later.
        """
        self.confman.set_value(
            "enabled_extensions",
            [plugin.module_name for plugin in self.plugin_engine.get_enabled_plugins()]
        )

    def show_settings_window(self, *args):
        settings_window = MirdorphSettingsWindow(application=self)
        settings_window.set_modal(True)
        settings_window.set_transient_for(self.main_win)
        settings_window.present()

    def show_about_dialog(self, *args):
        about_builder = Gtk.Builder.new_from_resource(
            "/org/gnome/gitlab/ranchester/Mirdorph/about_dialog.ui"
        )
        dialog = about_builder.get_object("about_dialog")
        dialog.set_modal(True)
        dialog.set_transient_for(self.main_win)
        dialog.present()

    def log_out(self, *args):
        keyring.delete_password("mirdorph", "token")
        self.relaunch()
    
    def create_inner_window_context(self, channel: int, flap: Adw.Flap):
        """
        Create  an inner window context, usually this is done automatically
        if none exists.

        param:
            channel: integer of the id of the channel
            flap: the AdwFlap that should be monitored for adaptiveness,
            you have to provide it here so that ChannelInnerWindows could be
            created while the main window isn't initialized yet.
        """
        context = ChannelInnerWindow(empty=False, channel=channel)
        flap.connect("notify::folded", context.handle_flap_folding)

        self.main_win.context_stack.add_child(context)
        self._inner_window_contexts[channel] = context

    def retrieve_inner_window_context(self, channel: int):
        """
        Retrieve an inner window context for a channel

        NOTE: If one does not already exist, it will be
        automatically created

        NOTE: should not be called if the main window isn't
        assigned yet.

        param:
            channel: integer of the id of the channel
        """
        if channel not in self._inner_window_contexts:
            self.create_inner_window_context(channel, self.main_win.main_flap)

        return self._inner_window_contexts[channel]

    def relaunch(self):
        logging.info("launching program duplicate instance")
        os.execv(sys.argv[0], sys.argv)
        logging.info("exiting initial program")
        os._exit(1)

def main(version, discord_loop, discord_client, keyring_exists):
    app = Application(discord_loop, discord_client, keyring_exists)
    return app.run(sys.argv)
