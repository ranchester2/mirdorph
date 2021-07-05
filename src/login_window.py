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
from gi.repository import Gtk, Gio, GLib, Adw
#from .discord_web_grabber import DiscordGrabber


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

        # If the secondary-text is long, even though it rewraps, the window
        # is first resized to the size it would be if the text couldn't wrap.
        # So we need to resize it again after that.
        self.set_resizable(True)
        self.resize(450, 1)

    def _on_adj_value_changed(self, adj: Gtk.Adjustment):
        bottom = adj.get_upper() - adj.get_page_size()
        if (abs(adj.get_value() - bottom) < sys.float_info.epsilon):
            self._understood_checkbutton.get_parent().set_sensitive(True)


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/login_window.ui")
class MirdorphLoginWindow(Adw.ApplicationWindow):
    __gtype_name__ = "MirdorphLoginWindow"

    _toplevel_deck: Adw.Deck = Gtk.Template.Child()
    _login_welcome_page: Gtk.Box = Gtk.Template.Child()

    _second_stage_stack: Gtk.Stack = Gtk.Template.Child()

    _login_token_page: Gtk.Box = Gtk.Template.Child()
    _login_token_entry: Gtk.Entry = Gtk.Template.Child()
    _login_token_entry_button: Gtk.Button = Gtk.Template.Child()

    _login_password_page: Gtk.Box = Gtk.Template.Child()
    _email_entry: Gtk.Entry = Gtk.Template.Child()
    _password_entry: Gtk.Entry = Gtk.Template.Child()
    _login_password_submit_button = Gtk.Template.Child()

    _graphical_login_button: Gtk.Button = Gtk.Template.Child()
    _login_graphical_page: Gtk.Box = Gtk.Template.Child()
    _login_graphical_page_webview_container: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_token_grabber()

        login_action_group = Gio.SimpleActionGroup()

        self._action_cancel = Gio.SimpleAction.new("cancel", None)
        self._action_cancel.connect("activate", lambda *_ : self.props.application.quit())
        login_action_group.add_action(self._action_cancel)

        self._action_back = Gio.SimpleAction.new("back", None)
        self._action_back.connect("activate", self._on_back)
        login_action_group.add_action(self._action_back)

        self._action_graphical_login = Gio.SimpleAction.new("with-graphical", None)
        self._action_graphical_login.connect("activate", self._on_graphical_login)
        login_action_group.add_action(self._action_graphical_login)

        self._action_token_login = Gio.SimpleAction.new("with-token", None)
        self._action_token_login.connect("activate", self._on_token_login)
        login_action_group.add_action(self._action_token_login)

        self._action_token_submit = Gio.SimpleAction.new("submit-token", None)
        self._action_token_submit.set_enabled(False)
        self._action_token_submit.connect("activate", self._on_token_login_submit)
        login_action_group.add_action(self._action_token_submit)

        self._action_password_login = Gio.SimpleAction.new("with-password", None)
        self._action_password_login.connect("activate", self._on_password_login)
        login_action_group.add_action(self._action_password_login)

        self._action_submit_password = Gio.SimpleAction.new("submit-password", None)
        self._action_submit_password.set_enabled(False)
        self._action_submit_password.connect("activate", self._on_password_login_submit)
        login_action_group.add_action(self._action_submit_password)

        self.insert_action_group("login", login_action_group)

        # UI file isn't enough with action-name
        self._graphical_login_button.grab_focus()

        if not self.props.application.confman.get_value("tos_notice_accepted"):
            # If directly shown in __init__, the login window would not be displayed yet.
            GLib.idle_add(self._show_tos_notice)

    def _build_token_grabber(self):
        try:
            self._token_grabber
        except AttributeError:
            pass
        else:
            self._login_graphical_page_webview_container.remove(
                self._token_grabber
            )
        # self._token_grabber = DiscordGrabber()
        self._token_grabber = Gtk.Label(label="Graphical login temporarily disabled while WebKitgtk doesn't support gtk4")
        # self._token_grabber.connect("login_complete", self._on_web_login_complete)
        # self._token_grabber.connect("login_failed", self._on_web_login_failed)
        self._token_grabber.show()
        self._login_graphical_page_webview_container.pack_start(
            self._token_grabber, True, True, 0)

    def _show_tos_notice(self):
        notice = TosNotice(modal=True, transient_for=self)
        response = notice.run()
        if response == Gtk.ResponseType.OK:
            self.props.application.confman.set_value(
                "tos_notice_accepted", True)
            notice.destroy()
        else:
            self.props.application.quit()

    def _on_token_login(self, *args):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_token_page)
        self._login_token_entry.grab_focus()
        self._login_token_entry_button.grab_default()

    def _on_password_login(self, *args):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_password_page)
        self._login_password_submit_button.grab_default()

    def _on_graphical_login(self, *args):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_graphical_page)

    def _on_back(self, *args):
        self._toplevel_deck.set_visible_child(self._login_welcome_page)

    @Gtk.Template.Callback()
    def _on_login_token_entry_changed(self, entry):
        self._action_token_submit.set_enabled(
            self._login_token_entry.get_text()
        )

    def _on_token_login_submit(self, *args):
        token = self._login_token_entry.get_text()
        self._login_token_entry.set_text("")
        self._save_token(token)
        self.props.application.relaunch()

    @Gtk.Template.Callback()
    def _on_password_warning_bar_response(self, bar: Gtk.InfoBar, response_id: int):
        if response_id == Gtk.ResponseType.CLOSE:
            bar.hide()

    @Gtk.Template.Callback()
    def _on_email_entry_activate(self, entry):
        if self._email_entry.get_text():
            self._password_entry.grab_focus()

    @Gtk.Template.Callback()
    def _on_password_entries_changed(self, entry):
        self._action_submit_password.set_enabled(
            self._email_entry.get_text() and self._password_entry.get_text()
        )

    def _on_password_login_submit(self, *args):
        self.set_sensitive(False)
        threading.Thread(target=self._token_password_retrieval_target).start()

    def _token_password_retrieval_target(self):
        email = self._email_entry.get_text()
        password = self._password_entry.get_text()
        payload = {
            "login": email,
            "password": password
        }
        r = requests.post(
            "https://discord.com/api/v9/auth/login", json=payload)
        if "token" in r.json():
            GLib.idle_add(
                self._token_generic_retrieval_gtk_target, r.json()["token"])
        else:
            logging.fatal(
                "Token not found in Discord Password login response, login failed. Incorrect password?")
            self.props.application.relaunch()

    def _on_web_login_complete(self, grabber, token: str):
        self._token_generic_retrieval_gtk_target(token)

    def _on_web_login_failed(self, grabber, help: str):
        self._build_token_grabber()

        dialog = Gtk.MessageDialog(
            buttons=Gtk.ButtonsType.OK,
            text="Login Failed",
            secondary_text=help,
            modal=True,
            transient_for=self
        )
        dialog.connect("response", lambda *_ : dialog.destroy())
        dialog.show()

    def _token_generic_retrieval_gtk_target(self, token):
        if token:
            self._save_token(token)
        self.props.application.relaunch()

    def _save_token(self, token: str):
        logging.info("setting token in keyring")
        keyring.set_password("mirdorph", "token", token)
        logging.info("token set in keyring")
