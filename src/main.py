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

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gdk, Gio, Handy

from .login_window import MirdorphLoginWindow
from .main_window import MirdorphMainWindow
from .event_manager import EventManager
from .channel_inner_window import ChannelInnerWindow
from .confman import ConfManager


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

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Handy.init()

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

        if self.keyring_exists:
            logging.info("launching with token")
            self.main_win = MirdorphMainWindow(application=self)

            # Weird place, temp
            self.load_channels(self.confman.get_value("added_channels"))

            self.main_win.present()
        else:
            logging.info("launching token retrieval sequence")
            win = self.props.active_window
            if not win:
                win = MirdorphLoginWindow(application=self)
            win.present()

    def load_channels(self, channels):
        for channel in channels:
            # Because might be called by reload_channels
            # and thus be called multiple times, we don't want
            # to create duplicate contexts, so if the context
            # already exists we don't do anything
            try:
                self.retrieve_inner_window_context(channel)
            except Exception as e:
                self.create_inner_window_context(channel, flap=self.main_win.main_flap)
                self.currently_running_channels.append(channel)
                self.main_win.channel_sidebar.inform_of_new_channel()

    def reload_channels(self, channels=None):
        # Just calls load_channels because it currently always fully
        # reloads channels anyways
        if channels is None:
            self.load_channels(self.currently_running_channels.copy())
        else:
            self.load_channels(channels)

    def create_inner_window_context(self, channel: int, flap: Handy.Flap):
        context = ChannelInnerWindow(empty=False, channel=channel)

        # So that it could handle folding
        # Here not in the init of ocntext, as then the app window
        # hasn't been created yet, so we need to get a reference from
        # it somehow before that
        flap.connect("notify::folded", context.handle_flap_folding)

        self.main_win.context_stack.add(context)
        self._inner_window_contexts[channel] = context

    # Temp until proper server support implemented
    def connect_channel(self, channel: int):
        self.main_win.channel_sidebar.add_channel(channel)

    def retrieve_inner_window_context(self, channel: int):
        return self._inner_window_contexts[channel]



def main(version, discord_loop, discord_client, keyring_exists):
    app = Application(discord_loop, discord_client, keyring_exists)
    return app.run(sys.argv)
