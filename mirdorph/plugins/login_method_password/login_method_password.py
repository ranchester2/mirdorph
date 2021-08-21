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

from __future__ import annotations
import threading
import logging
import gi
import requests
from gettext import gettext as _
from gi.repository import Gtk, Gio, GLib
from mirdorph.plugin import MrdLoginMethodPlugin


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/plugins/login_method_password/password_login_page.ui")
class PasswordLoginPage(Gtk.Overlay):
    __gtype_name__ = "PasswordLoginPage"

    _submit_button: Gtk.Button = Gtk.Template.Child()
    _email_entry: Gtk.Entry = Gtk.Template.Child()
    _password_entry: Gtk.PasswordEntry = Gtk.Template.Child()

    def __init__(self, plugin: LoginMethodPassword, *args, **kwargs):
        Gtk.Overlay.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        # Way to emit the token obtained signal from here
        self._plugin = plugin
        self._plugin.headerbar.pack_end(self._submit_button)

        # Hack:
        # action groups don't work on non-children, which this button is due to the headerbar separation,
        # so instead we add it to the global application, and use a fake prefix to indicate that this really
        # isn't an application-global action.
        self._action_password_submit = Gio.SimpleAction.new("fake-prefix-password-login-submit", None)
        self._action_password_submit.set_enabled(False)
        self._action_password_submit.connect("activate", self._on_submit)
        self.app.add_action(self._action_password_submit)

    @Gtk.Template.Callback()
    def _on_warning_bar_response(self, bar: Gtk.InfoBar, response_id: Gtk.ResponseType):
        if response_id == Gtk.ResponseType.CLOSE:
            bar.hide()

    @Gtk.Template.Callback()
    def _on_email_entry_activate(self, entry):
        if self._email_entry.get_text():
            self._password_entry.grab_focus()

    @Gtk.Template.Callback()
    def _on_credentials_entries_changed(self, entry):
        self._action_password_submit.set_enabled(
            self._email_entry.get_text() and self._password_entry.get_text()
        )

    @Gtk.Template.Callback()
    def _on_map(self, widget):
        window = self.get_native()
        window.set_default_widget(self._submit_button)

    @Gtk.Template.Callback()
    def _on_unmap(self, widget):
        self._plugin.headerbar.remove(self._submit_button)

    def _on_submit(self, *args):
        window = self.get_native()
        window.set_sensitive(False)
        threading.Thread(target=self._token_retrieval_target).start()

    def _token_retrieval_target(self):
        email = self._email_entry.get_text()
        password = self._password_entry.get_text()
        payload = {
            "login": email,
            "password": password
        }
        r = requests.post(
            "https://discord.com/api/v9/auth/login", json=payload)
        if "token" in r.json():
            GLib.idle_add(self._plugin.emit, "token-obtained", r.json()["token"])
        else:
            logging.fatal(
                "Token not found in Discord Password login response, login failed. Incorrect password?")
            GLib.idle_add(self.app.relaunch)


class LoginMethodPassword(MrdLoginMethodPlugin):
    def __init__(self):
        super().__init__()
        self.method_human_name = _("Username and Password")
        self._page = None

    def load(self, login_method_cont):
        self._page = PasswordLoginPage(self)
        login_method_cont.set_child(self._page)

    def unload(self, login_method_cont):
        login_method_cont.set_child(None)
        self._page = None
