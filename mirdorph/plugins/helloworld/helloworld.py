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
from gi.repository import Adw, Gtk, Gio, GObject
from mirdorph.plugin import MrdApplicationPlugin

BYE_MESSAGE_CONFMAN_KEY = "helloworld_plugin_goodbye_message"
DEFAULT_BYE_MESSAGE = "Bye, World"

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/plugins/helloworld/configuration.ui")
class HelloSettingsPage(Adw.Clamp):
    __gtype_name__ = "HelloSettingsPage"

    _message_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(self, current_goodbye_message: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = Gio.Application.get_default()
        self._message_entry.set_text(current_goodbye_message)

    @Gtk.Template.Callback()
    def _on_map(self, widget):
        self._message_entry.grab_focus()

    @Gtk.Template.Callback()
    def _on_message_entry_changed(self, entry):
        self.app.confman.set_value(BYE_MESSAGE_CONFMAN_KEY, self._message_entry.get_text())


class HelloWorldPlugin(MrdApplicationPlugin):
    def __init__(self):
        super().__init__()
        self.app = Gio.Application.get_default()
        self._welcome_message = Gio.resources_lookup_data(
            "/org/gnome/gitlab/ranchester/Mirdorph/plugins/helloworld/welcome_message.txt", 0
        ).get_data().decode("utf-8")
        try:
            self._goodbye_message = self.app.confman.get_value(BYE_MESSAGE_CONFMAN_KEY)
        except KeyError:
            self._goodbye_message = DEFAULT_BYE_MESSAGE
        self.app.confman.connect("setting-changed", self._on_confman_setting_changed)

    def _on_confman_setting_changed(self, confman, setting_name: str):
        if setting_name == BYE_MESSAGE_CONFMAN_KEY:
            self._goodbye_message = self.app.confman.get_value(BYE_MESSAGE_CONFMAN_KEY)

    def load(self):
        print(self._welcome_message)

    def unload(self):
        print(self._goodbye_message)

    def get_configuration_widget(self):
        return HelloSettingsPage(self._goodbye_message)
