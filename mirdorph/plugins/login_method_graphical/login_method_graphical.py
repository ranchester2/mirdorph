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

import gi
from gettext import gettext as _
from gi.repository import Adw, Gtk
from mirdorph.plugin import MrdLoginMethodPlugin
from .discord_web_grabber import DiscordGrabber


class LoginMethodGraphical(MrdLoginMethodPlugin):
    def __init__(self):
        super().__init__()
        self.method_human_name = _("Graphical Login")
        self.is_primary = True

        self._login_method_cont = None
        self._grabber = None

    def load(self, login_method_cont):
        # Useful to directly have a reference of it for rebuilding it on failure
        self._login_method_cont = login_method_cont
        self._build_token_grabber()

    def unload(self, login_method_cont):
        self._grabber = None
        self._login_method_cont = None
        # We may not have this reference, so we should use the supplied one to avoid
        # headaches.
        login_method_cont.set_child(None)

    def _build_token_grabber(self):
        """
        Build the DiscordGrabber and configure it for usage, add it to the method
        container.

        This is useful if you need to build it multiple times: for example if
        login failed.

        The container is the login method container at `self._login_method_cont`
        """
        self._grabber = DiscordGrabber()
        self._grabber.connect("login-complete", lambda grabber, token : self.emit("token-obtained", token))
        self._grabber.connect("login-failed", self._on_login_failed)
        self._login_method_cont.set_child(self._grabber)

    def _on_login_failed(self, grabber, help: str):
        self._grabber = None
        self._login_method_cont.set_child(None)
        self._build_token_grabber()

        dialog = Gtk.MessageDialog(
           buttons=Gtk.ButtonsType.OK,
           text="Login Failed",
           secondary_text=help,
           modal=True,
           transient_for=self._grabber.get_native()
        )
        dialog.connect("response", lambda *_ : dialog.destroy())
        dialog.show()
 
