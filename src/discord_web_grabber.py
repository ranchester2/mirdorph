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

import os
import gi
import logging
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, GObject, WebKit2


class DiscordGrabber(WebKit2.WebView):
    """
    A custom Discord Web-based token grabber implementation.

    Created because discordlogin by diamondburned kind of sucks
    in some ways. However still has issues with narrow window
    size and new background.

    To use, create the widget and listen for the "login-complete"
    signal, it has the token as an str argument.
    """
    __gtype_name__ =  "DiscordGrabber"

    __gsignals__ = {
        'login_complete': (GObject.SIGNAL_RUN_FIRST, None,
                      (str,))
    }

    def __init__(self, *args, **kwargs):
        WebKit2.WebView.__init__(self, is_ephemeral=True, *args, **kwargs)
        self._inital_exec = False
        self.get_context().register_uri_scheme("token", self._token_uri_callback)
        self.connect("load-changed", self._on_load_changed)
        self.connect("resource-load-started", self._on_resource_load_started)
        with open(os.path.join(os.path.dirname(__file__), "get_token.js"), 'r') as f:
            self._grabber_injection = f.read()

        self.load_uri("https://discord.com/login")

    def _on_load_changed(self, webview, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED and not self._inital_exec:
            self._inital_exec = True
            self.run_javascript(self._grabber_injection, None, None, None)

    def do_login_complete(self, token: str):
        pass

    def _token_uri_callback(self, request):
        self.emit("login_complete", request.get_uri()[len("token://"):])
        # We don't want discord to be continued being displayed instead
        self.load_uri("http://www.blankwebsite.com")

    def _on_resource_load_started(self, webview, resource, request):
        if request.get_uri() == "https://discord.com/app":
            # When we fail to get the token, we go on to load /app.
            logging.fatal("FATAL: RETRIEVING TOKEN FAILED. XLLHTTP BYPASS COMPLETE")
            raise Exception("Token not captured, this could be because either the window is too narrow or the background is colorful.")
