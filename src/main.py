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


class Application(Gtk.Application):
    def __init__(self, discord_loop, discord_client, keyring_exists=False):
        super().__init__(application_id='org.gnome.gitlab.ranchester.Mirdorph',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.discord_loop = discord_loop
        self.discord_client = discord_client
        self.keyring_exists = keyring_exists
        self.event_manager = EventManager()
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
            self.main_win.present()
        else:
            logging.info("launching token retrieval sequence")
            win = self.props.active_window
            if not win:
                win = MirdorphLoginWindow(application=self)
            win.present()

    def create_inner_window_context(self, channel: int, bar_size_group: Gtk.SizeGroup):
        context = ChannelInnerWindow(empty=False, channel=channel, bar_size_group=bar_size_group)
        self._inner_window_contexts[channel] = context

    def retrieve_inner_window_context(self, channel: int):
        return self._inner_window_contexts[channel]



def main(version, discord_loop, discord_client, keyring_exists):
    app = Application(discord_loop, discord_client, keyring_exists)
    return app.run(sys.argv)
