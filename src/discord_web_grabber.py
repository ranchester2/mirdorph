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
import random
import gi
gi.require_version("WebKit2", "4.0")
from gi.repository import Gtk, GObject, WebKit2
from gettext import gettext as _


class DiscordGrabber(WebKit2.WebView):
    """
    A custom Discord Web-based token grabber implementation.

    Created because discordlogin by diamondburned kind of sucks
    in some ways.

    To use, create the widget and listen for the "login-complete"
    signal, it has the token as an argument.

    The "login-failed" signal is emitted if it fails (comes with
    suggested help)
    """
    __gtype_name__ =  "DiscordGrabber"

    __gsignals__ = {
        "login_complete": (GObject.SIGNAL_RUN_FIRST, None,
                      (str,)),
        "login_failed": (GObject.SIGNAL_RUN_FIRST, None,
                      (str,))
    }

    LOGIN_TROUBLESHOOT = _("Make sure the window isn't narrow.")

    def __init__(self, *args, **kwargs):
        WebKit2.WebView.__init__(self, is_ephemeral=True, *args, **kwargs)
        # URI schemes - how to send data from Javascript.
        # WebKitGtk doesn't seem to have an easy way to call host python code from
        # javascript, however we can register a custom URI scheme,
        # and put the data we want to send in the path. And trying to open
        # an arbitrary URI is easy in Javascript.

        # WebKit stores registered URI schemes globally, and fails if multiple of the same
        # are registered. We can't check which ones are registered easily, however we
        # can make them random to make this extremely unlikely.
        self.SCHEME_ID = random.randrange(1, 100000)
        self._scheme = f"token{str(self.SCHEME_ID)}"

        self.get_context().register_uri_scheme(self._scheme, self._token_uri_callback)

        # The js file can't immediately contain the scheme id, as it is unique
        with open(os.path.join(os.path.dirname(__file__), "get_token.js"), "r") as f:
            self._injection_code = f"var scheme_id = {self.SCHEME_ID}\n{f.read()}"

        self.connect("resource-load-started", self._on_resource_load_started)

        # The Javascript can not be loaded after the website, as then it is overriden.
        # However we can't just run it after load_uri either, as that will still get
        # it overriden. Listening to ::load-changed allows us to know when exactly
        # the website is fully loaded, which is when we need to inject the Javascript.
        self._initial_exec = False
        self.connect("load-changed", self._on_load_changed)
        self.load_uri("https://discord.com/login")

    def _on_load_changed(self, webview, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED and not self._initial_exec:
            self._initial_exec = True
            self.run_javascript(self._injection_code, None, None, None)

    def _token_uri_callback(self, request: WebKit2.URISchemeRequest):
        self.emit("login_complete", request.get_uri()[len(f"{self._scheme}://"):])
        # We don't want discord to be continued being displayed
        self.load_uri("http://www.blankwebsite.com")

    def _on_resource_load_started(self, webview, resource, request):
        # If the token isn't grabbed, we will go on to load the discord Application,
        # this indicates failure.
        if request.get_uri() == "https://discord.com/app":
            self.emit("login_failed", self.LOGIN_TROUBLESHOOT)
