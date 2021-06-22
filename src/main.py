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
import gi
import logging
import os
import shutil
import keyring

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, Gio, Handy
from pathlib import Path
from .login_window import MirdorphLoginWindow
from .main_window import MirdorphMainWindow
from .event_manager import EventManager
from .channel_inner_window import ChannelInnerWindow
from .confman import ConfManager
from .settings_window import MirdorphSettingsWindow


class Application(Gtk.Application):

    def __init__(self, discord_loop, discord_client, keyring_exists=False):
        super().__init__(application_id='org.gnome.gitlab.ranchester.Mirdorph',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.discord_loop = discord_loop
        self.discord_client = discord_client
        self.keyring_exists = keyring_exists

        self.confman = ConfManager()
        self.event_manager = EventManager()

        self.currently_running_channels = []
        self._inner_window_contexts = {}

        # Why the custom member cache? Doesn't discord.py have one?
        # Yes, however it usually doesn't actually work, which leads to doing
        # a billion calls for getting a member from a guild to get the username
        # color for the author of a message. We can optimise quite a lot by
        # implementing this custom cache.
        self.custom_member_cache = {}

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()
        actions = [
            {
                'name': 'settings',
                'func': self.show_settings_window,
                'accel': '<Primary>comma'
            },
            {
                'name': 'about',
                'func': self.show_about_dialog
            },
            {
                'name': 'logout',
                'func': self.log_out
            },
            {
                'name': 'search-guilds',
                'func': self.search_guilds,
                'accel': '<Primary>k'
            }
        ]

        for a in actions:
            c_action = Gio.SimpleAction.new(a['name'], None)
            c_action.connect('activate', a['func'])
            self.add_action(c_action)
            if 'accel' in a.keys():
                self.set_accels_for_action(
                    f'app.{a["name"]}',
                    [a['accel']]
                )

    def do_activate(self):
        stylecontext = Gtk.StyleContext()
        provider = Gtk.CssProvider()
        provider.load_from_resource(
            f'/org/gnome/gitlab/ranchester/Mirdorph/ui/gtk_style.css'
        )
        stylecontext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        logging.info("clearing cache")
        cache_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))
        # For first launch
        cache_dir_path.mkdir(exist_ok=True)
        shutil.rmtree(cache_dir_path)
        cache_dir_path.mkdir(parents=True, exist_ok=True)

        if self.keyring_exists:
            logging.info("launching with token")
            # A lot of things break with multiple windows,
            # while this still creats multiple discord clients,
            # it prevents further damage.
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

    def show_settings_window(self, *args):
        settings_window = MirdorphSettingsWindow(application=self)
        self.add_window(settings_window)

        settings_window.set_modal(True)
        settings_window.set_transient_for(self.main_win)
        settings_window.present()

    def show_about_dialog(self, *args):
        about_builder = Gtk.Builder.new_from_resource(
            '/org/gnome/gitlab/ranchester/Mirdorph/about_dialog.ui'
        )
        dialog = about_builder.get_object('about_dialog')
        dialog.set_modal(True)
        dialog.set_transient_for(self.main_win)
        dialog.present()

    def log_out(self, *args):
        keyring.delete_password("mirdorph", "token")
        self.relaunch()
    
    def search_guilds(self, *args):
        self.main_win.channel_sidebar.guild_list_search_bar.set_search_mode(True)

    def create_inner_window_context(self, channel: int, flap: Handy.Flap):
        context = ChannelInnerWindow(empty=False, channel=channel)

        # So that it could handle folding
        # Here not in the init of context, as then the app window
        # hasn't been created yet, so we need to get a reference from
        # it somehow before that
        flap.connect("notify::folded", context.handle_flap_folding)

        self.main_win.context_stack.add(context)
        self._inner_window_contexts[channel] = context

    def retrieve_inner_window_context(self, channel: int):
        """
        Retrieve an inner window context for a channel

        NOTE: If one does not already exist, it will be
        automatically created

        param:
            channel: integer of the id of the channel
        """
        if channel not in self._inner_window_contexts:
            self.create_inner_window_context(channel, self.main_win.main_flap)

        return self._inner_window_contexts[channel]

    def do_error(self, error_title: str, error_body: str):
        """
        Display an error (Discord) in the application.

        param:
            error_title: The abstract title of the type of the widget
            error_body: More advanced text of the error
        """
        self.main_win.display_err_priv(error_title, error_body)

    def relaunch(self):
        logging.info("launching program duplicate instance")
        os.execv(sys.argv[0], sys.argv)
        logging.info("exiting initial program")
        os._exit(1)

def main(version, discord_loop, discord_client, keyring_exists):
    app = Application(discord_loop, discord_client, keyring_exists)
    return app.run(sys.argv)
