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
import sys
import keyring
import logging
import threading
import requests
from gettext import gettext as _
from gi.repository import Adw, Gtk, Gio, GLib, GObject
from .plugin import MrdPluginInfo, MrdExtensionSet, MrdLoginMethodPlugin


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/tos_notice.ui")
class TosNotice(Gtk.MessageDialog):
    __gtype_name__ = "TosNotice"

    _tos_textview: Gtk.TextView = Gtk.Template.Child()
    _tos_scrolled_win: Gtk.ScrolledWindow = Gtk.Template.Child()
    _understood_checkbutton: Gtk.CheckButton = Gtk.Template.Child()

    def __init__(self, *args, **kwargs):
        Gtk.MessageDialog.__init__(self, *args, **kwargs)

        tos_text_rd = Gio.resources_lookup_data(
            "/org/gnome/gitlab/ranchester/Mirdorph/tos.txt", 0)
        tos_text = tos_text_rd.get_data().decode("utf-8")

        self._tos_textview.get_buffer().set_text(tos_text)

        self._tos_scrolled_win.get_vadjustment().connect(
            "value-changed", self._on_adj_value_changed)

        self.get_widget_for_response(Gtk.ResponseType.CANCEL).grab_focus()

    def _on_adj_value_changed(self, adj: Gtk.Adjustment):
        bottom = adj.get_upper() - adj.get_page_size()
        if (abs(adj.get_value() - bottom) < sys.float_info.epsilon):
            self._understood_checkbutton.set_sensitive(True)


class LoginButton(Gtk.Button):
    plugin = GObject.Property(type=MrdPluginInfo)

    def __init__(self, plugin, *args, **kwargs):
        Gtk.Button.__init__(self, width_request=250, *args, **kwargs)
        self.plugin = plugin
        self.add_css_class("login-button")
        if self.plugin.u_activatable.is_primary:
            self.show_as_primary()
        else:
            self.set_label(self.plugin.u_activatable.method_human_name)

    def show_as_primary(self):
        """
        Make the button show up as if it was the primary login method,
        even if the underlying plugin does not say that.

        This is useful as a fallback case if no other methods are availabel.
        """
        self.set_label(_("Log In"))
        self.add_css_class("suggested-action")

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/login_window.ui")
class MirdorphLoginWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MirdorphLoginWindow"

    _toplevel_deck: Adw.Leaflet = Gtk.Template.Child()
    _login_welcome_page: Gtk.Box = Gtk.Template.Child()

    _login_method_page: Gtk.Box = Gtk.Template.Child()
    _login_method_headerbar: Adw.HeaderBar = Gtk.Template.Child()
    _login_method_content_cont: Adw.Bin = Gtk.Template.Child()

    _login_method_button_box: Gtk.Box = Gtk.Template.Child()
    _advanced_login_method_button_box: Gtk.Box = Gtk.Template.Child()
    _advanced_login_method_expander: Gtk.Expander = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        login_action_group = Gio.SimpleActionGroup()

        self._action_cancel = Gio.SimpleAction.new("cancel", None)
        self._action_cancel.connect("activate", lambda *_ : self.props.application.quit())
        login_action_group.add_action(self._action_cancel)

        self._action_back = Gio.SimpleAction.new("back", None)
        self._action_back.connect("activate", self._on_back)
        login_action_group.add_action(self._action_back)

        self.insert_action_group("login", login_action_group)

        self._currently_shown_login_method_plugin = None
        self._primary_login_button = None
        self._advanced_login_buttons = []
        self._extension_set = MrdExtensionSet(
            self.props.application.plugin_engine,
            MrdLoginMethodPlugin
        )

        def setup_plugin(plugin):
            plugin.u_activatable.connect("token-obtained", self._on_plugin_token_obtained)
            login_button = LoginButton(
                plugin,
                halign=Gtk.Align.CENTER
            )
            login_button.connect("clicked", self._on_login_method_button_clicked)
            if login_button.plugin.u_activatable.is_primary:
                self._primary_login_button = login_button
                self._login_method_button_box.append(login_button)
            else:
                self._advanced_login_buttons.append(login_button)
                self._advanced_login_method_button_box.append(login_button)
                self._advanced_login_method_expander.show()

        def on_extension_removed(extension_set, plugin: MrdPluginInfo):
            if self._primary_login_button and self._primary_login_button.plugin == plugin:
                self._login_method_button_box.remove(self._primary_login_button)
                self._primary_login_button = None
            else:
                try:
                    login_button = [button for button in self._advanced_login_buttons if button.plugin == plugin][0]
                except IndexError:
                    return
                else:
                    if plugin == login_button.plugin:
                        self._advanced_login_buttons.remove(login_button)
                        self._advanced_login_method_button_box.remove(login_button)

        for plugin in self._extension_set:
            setup_plugin(plugin)
                
        self._extension_set.connect("extension_added", lambda set, plugin : setup_plugin(plugin))
        self._extension_set.connect("extension_removed", on_extension_removed)

        # If a primary method is not enabled, one of the advanced methods
        # should be designated as the primary method.
        if not self._primary_login_button and self._advanced_login_buttons:
            first_login_method = self._advanced_login_buttons[0]
            first_login_method.show_as_primary()

            self._advanced_login_method_button_box.remove(first_login_method)
            self._advanced_login_buttons.remove(first_login_method)

            self._login_method_button_box.append(first_login_method)
            self._primary_login_button = first_login_method

            if not self._advanced_login_buttons:
                self._advanced_login_method_expander.hide()

        if self._primary_login_button:
            self._primary_login_button.grab_focus()

        if not self.props.application.confman.get_value("tos_notice_accepted"):
            # The window must be created first before transient_for works
            GLib.idle_add(self._show_tos_notice)

    def _show_tos_notice(self):
        notice = TosNotice(modal=True, transient_for=self)
        notice.connect("response", self._on_tos_notice_response)
        notice.show()

    def _on_tos_notice_response(self, dialog: TosNotice, response: int):
        if response == Gtk.ResponseType.OK:
            self.props.application.confman.set_value(
                "tos_notice_accepted", True)
            dialog.destroy()
        else:
            self.props.application.quit()

    @Gtk.Template.Callback()
    def _on_login_method_map(self, widget):
        self._currently_shown_login_method_plugin.u_activatable.set_property("headerbar", self._login_method_headerbar)
        self._currently_shown_login_method_plugin.u_activatable.load(self._login_method_content_cont)

    @Gtk.Template.Callback()
    def _on_login_method_unmap(self, widget):
        self._currently_shown_login_method_plugin.u_activatable.set_property("headerbar", None)
        self._currently_shown_login_method_plugin.u_activatable.unload(self._login_method_content_cont)

    def _on_login_method_button_clicked(self, button: LoginButton):
        self._currently_shown_login_method_plugin = button.plugin
        self._toplevel_deck.set_visible_child(self._login_method_page)

    def _on_back(self, *args):
        if self._currently_shown_login_method_plugin:
            self._currently_shown_login_method_plugin.u_activatable.unload(self._login_method_content_cont)
        self._toplevel_deck.set_visible_child(self._login_welcome_page)

    def _on_plugin_token_obtained(self, plugin, token: str):
        self._save_token(token)
        self.props.application.relaunch()

    def _save_token(self, token: str):
        logging.info("setting token in keyring")
        keyring.set_password("mirdorph", "token", token)
        logging.info("token set in keyring")
