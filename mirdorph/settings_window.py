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

from gettext import gettext as _
from gi.repository import Adw, Gtk, Gio, GObject
from mirdorph.plugin import MrdPluginInfo


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/extension_row.ui")
class ExtensionRow(Adw.ActionRow):
    __gtype_name__ = "ExtensionRow"

    plugin = GObject.Property(type=MrdPluginInfo)

    _settings_button: Gtk.Button = Gtk.Template.Child()
    _is_active_switch: Gtk.Switch = Gtk.Template.Child()

    def __init__(self, plugin: MrdPluginInfo, preferences_window: Adw.PreferencesWindow, *args, **kwargs):
        Adw.ExpanderRow.__init__(self, *args, **kwargs)
        self.plugin = plugin
        self._preferences_window = preferences_window
        # GtkExpression directly in the UI file would be better, however after a lot
        # of trying I found out it doesn't work in PyGObject. When it gets support,
        # this should be easily changable to <binding> and <lookup> in the UI file
        self.plugin.bind_property("name", self, "title", GObject.BindingFlags.SYNC_CREATE)
        self.plugin.bind_property("description", self, "subtitle", GObject.BindingFlags.SYNC_CREATE)
        self.plugin.bind_property("configurable", self._settings_button, "sensitive", GObject.BindingFlags.SYNC_CREATE)
        # SYNC_CREATE alone isn't enough for changing the property here to change it on the plugin object,
        # so for properties that can change at runtime, binding them again with different flags is needed too.
        self.plugin.bind_property("active", self._is_active_switch, "active", GObject.BindingFlags.SYNC_CREATE)
        self.plugin.bind_property("active", self._is_active_switch, "active", GObject.BindingFlags.BIDIRECTIONAL)

    @Gtk.Template.Callback()
    def _on_settings_button_clicked(self, button):
        self._preferences_window.present_extension_configuration(self.plugin)


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/settings_window.ui")
class MirdorphSettingsWindow(Adw.PreferencesWindow):
    __gtype_name__ = "MirdorphSettingsWindow"

    _send_typing_switch: Gtk.Switch = Gtk.Template.Child()
    _preview_links_switch: Gtk.Switch = Gtk.Template.Child()

    _extensions_pref_group: Adw.PreferencesGroup = Gtk.Template.Child()

    _configuration_page: Gtk.Box = Gtk.Template.Child()
    _configuration_window_title: Adw.WindowTitle = Gtk.Template.Child()
    _configuration_content: Adw.Bin = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Adw.PreferencesWindow.__init__(self, *args, **kwargs)
        self._init_values()
        self._init_extensions()

    def _init_values(self):
        self._send_typing_switch.set_state(
            self.props.application.confman.get_value("send_typing_events")
        )
        self._preview_links_switch.set_state(
            self.props.application.confman.get_value("preview_links")
        )

    def _init_extensions(self):
        for plugin in self.props.application.plugin_engine.get_available_plugins():
            extension_row = ExtensionRow(plugin, self)
            self._extensions_pref_group.add(extension_row)

    def present_extension_configuration(self, plugin: MrdPluginInfo):
        """
        Present the configuration settings of a configurable plugin to
        the user.

        param:
            plugin: the configurable `MrdPluginInfo` settings' you want to present
        """
        self._configuration_window_title.set_title(_("{} Settings").format(plugin.name))
        self._configuration_content.set_child(plugin.u_activatable.get_configuration_widget())
        self.present_subpage(
            self._configuration_page
        )

    @Gtk.Template.Callback()
    def _on_configuration_close(self, *args):
        self.close_subpage()

    @Gtk.Template.Callback()
    def _on_send_typing_switch_state_set(self, switch: Gtk.Switch, state: bool):
        self.props.application.confman.set_value("send_typing_events", state)

    @Gtk.Template.Callback()
    def _on_preview_links_switch_state_set(self, switch: Gtk.Switch, state: bool):
        self.props.application.confman.set_value("preview_links", state)
