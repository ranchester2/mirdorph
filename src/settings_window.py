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

from gi.repository import Gtk, Gio, Handy


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/settings_window.ui")
class MirdorphSettingsWindow(Handy.PreferencesWindow):
    __gtype_name__ = "MirdorphSettingsWindow"

    _send_typing_switch: Gtk.Switch = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Handy.PreferencesWindow.__init__(self, *args, **kwargs)
        self._init_values()

    def _init_values(self):
        self._send_typing_switch.set_state(
            self.props.application.confman.get_value("send_typing_events")
        )

    @Gtk.Template.Callback()
    def _on_send_typing_switch_state_set(self, switch: Gtk.Switch, state: bool):
        self.props.application.confman.set_value("send_typing_events", state)
