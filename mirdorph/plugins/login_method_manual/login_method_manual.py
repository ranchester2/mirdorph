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
import gi
from gettext import gettext as _
from gi.repository import Adw, Gtk, Gio, GLib
from mirdorph.plugin import MrdLoginMethodPlugin


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/plugins/login_method_manual/manual_login_page.ui")
class ManualLoginPage(Adw.Clamp):
    __gtype_name__ = "ManualLoginPage"

    _token_entry: Gtk.Entry = Gtk.Template.Child()
    _token_submit_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, plugin: LoginMethodManual, *args, **kwargs):
        Adw.Clamp.__init__(self, *args, **kwargs)
        # Way to emit the token obtained signal from here
        self._plugin = plugin
        self._manual_login_action_group = Gio.SimpleActionGroup()

        self._action_token_submit = Gio.SimpleAction.new("submit", None)
        self._action_token_submit.set_enabled(False)
        self._action_token_submit.connect("activate", self._on_token_submit)
        self._manual_login_action_group.add_action(self._action_token_submit)

        self.insert_action_group("manual-login", self._manual_login_action_group)

    @Gtk.Template.Callback()
    def _on_token_entry_changed(self, entry):
        self._action_token_submit.set_enabled(
            self._token_entry.get_text()
        )

    # Not entirely sure if this is how to correctly set the default widgets
    # and focus here
    @Gtk.Template.Callback()
    def _on_map(self, widget):
        window = self.get_native()
        # GLib.idle_add needed after first map, works correclty without it on first,
        # but not on subsequent uses
        GLib.idle_add(window.set_default_widget, self._token_submit_button)
        # grab_focus returns positive, causing infinite repetition
        GLib.idle_add(lambda *_ : self._token_entry.grab_focus() and 0)

    def _on_token_submit(self, *args):
        token = self._token_entry.get_text()
        self._token_entry.set_text("")
        self._plugin.emit("token-obtained", token)


class LoginMethodManual(MrdLoginMethodPlugin):
    def __init__(self):
        super().__init__()
        self.method_human_name = _("Manual Token")
        self._page = None

    def load(self, login_method_cont):
        self._page = ManualLoginPage(self)
        login_method_cont.set_child(self._page)

    def unload(self, login_method_cont):
        login_method_cont.set_child(None)
        self._page = None
