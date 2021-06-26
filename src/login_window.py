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
import subprocess
import threading
import requests
import time
from gi.repository import Gtk, Gio, Gdk, GLib, Handy
from .discord_web_grabber import DiscordGrabber


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

    def _on_adj_value_changed(self, adj):
        bottom = adj.get_upper() - adj.get_page_size()
        if (abs(adj.get_value() - bottom) < sys.float_info.epsilon):
            self._understood_checkbutton.get_parent().set_sensitive(True)


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/login_window.ui")
class MirdorphLoginWindow(Handy.ApplicationWindow):
    __gtype_name__ = "MirdorphLoginWindow"

    _toplevel_deck = Gtk.Template.Child()
    _login_welcome_page = Gtk.Template.Child()

    _second_stage_stack = Gtk.Template.Child()

    _login_token_page = Gtk.Template.Child()
    _login_token_entry = Gtk.Template.Child()
    _login_token_entry_button = Gtk.Template.Child()

    _login_password_page = Gtk.Template.Child()
    _email_entry = Gtk.Template.Child()
    _password_entry = Gtk.Template.Child()
    _finish_password_login_button = Gtk.Template.Child()

    _login_graphical_page = Gtk.Template.Child()
    _login_graphical_page_webview_container = Gtk.Template.Child()

    _notification_revealer = Gtk.Template.Child()
    _notification_title_label = Gtk.Template.Child()
    _notification_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_token_grabber()

        if not self.props.application.confman.get_value("tos_notice_accepted"):
            # If directly shown in __init__, the login window would not be displayed yet.
            GLib.idle_add(self._show_tos_notice)

    def _build_token_grabber(self):
        try:
            self._token_grabber
        except AttributeError:
            pass
        else:
            self._token_grabber.destroy()
        self._token_grabber = DiscordGrabber()
        self._token_grabber.connect("login_complete", self._on_web_login_complete)
        self._token_grabber.connect("login_failed", self._on_web_login_failed)
        self._token_grabber.show()
        self._login_graphical_page_webview_container.pack_start(self._token_grabber, True, True, 0)

    def _show_tos_notice(self):
        notice = TosNotice(modal=True, transient_for=self)
        response = notice.run()
        if response == Gtk.ResponseType.OK:
            self.props.application.confman.set_value("tos_notice_accepted", True)
            notice.destroy()
        else:
            os._exit(0)

    @Gtk.Template.Callback()
    def _on_token_button_clicked(self, button):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_token_page)

    @Gtk.Template.Callback()
    def _on_password_button_clicked(self, button):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_password_page)

    @Gtk.Template.Callback()
    def _on_second_stage_back_buttons_clicked(self, button):
        self._toplevel_deck.set_visible_child(self._login_welcome_page)

    @Gtk.Template.Callback()
    def _on_main_cancel_button_clicked(self, button):
        os._exit(1)

    @Gtk.Template.Callback()
    def _on_password_warning_bar_response(self, bar, response_id: int):
        if response_id == Gtk.ResponseType.CLOSE:
            bar.hide()

    @Gtk.Template.Callback()
    def _on_password_entries_changed(self, entry):
        self._finish_password_login_button.set_sensitive(
            self._email_entry.get_text() and self._password_entry.get_text()
        )

    def _do_init_password_login(self):
        self.set_sensitive(False)
        threading.Thread(target=self._token_password_retrieval_target).start()

    @Gtk.Template.Callback()
    def _on_email_entry_activate(self, entry):
        if self._email_entry.get_text():
            self._password_entry.grab_focus()

    @Gtk.Template.Callback()
    def _on_password_entry_activate(self, entry):
        if self._email_entry.get_text() and self._password_entry.get_text():
            self._do_init_password_login()

    @Gtk.Template.Callback()
    def _on_finish_password_login_button_clicked(self, button):
        self._do_init_password_login()

    @Gtk.Template.Callback()
    def _on_login_token_entry_changed(self, entry):
        self._login_token_entry_button.get_style_context().add_class("suggested-action")

    @Gtk.Template.Callback()
    def _on_main_login_button_clicked(self, button):
        self._toplevel_deck.set_visible_child(self._second_stage_stack)
        self._second_stage_stack.set_visible_child(self._login_graphical_page)

    def _on_web_login_complete(self, grabber, token: str):
        self._token_generic_retrieval_gtk_target(token)

    def _on_web_login_failed(self, grabber, help: str):
        self._build_token_grabber()
        # Currently notification code is copy pasted from main window
        # But is there a better way?
        self._notification_label.set_label(help)
        self._notification_title_label.set_label("Error")
        self._notification_revealer.set_reveal_child(True)

        GLib.timeout_add_seconds(5, self._notification_waiting_gtk_target)

    def _notification_waiting_gtk_target(self):
        self._notification_revealer.set_reveal_child(False)
        return False

    def _token_password_retrieval_target(self):
        email = self._email_entry.get_text()
        password = self._password_entry.get_text()
        payload = {
            "login": email,
            "password": password
        }
        r = requests.post("https://discord.com/api/v9/auth/login", json=payload)
        if "token" in r.json():
            GLib.idle_add(self._token_generic_retrieval_gtk_target, r.json()["token"])
        else:
            logging.fatal("Token not find in Discord Password login response, login failed")
            self.props.application.relaunch()

    def _token_web_retrieval_target(self):
        token = subprocess.check_output("discordlogin", shell=True, text=True)
        GLib.idle_add(self._token_generic_retrieval_gtk_target, token)

    def _token_generic_retrieval_gtk_target(self, token):
        if token:
            self._save_token(token)
        self.props.application.relaunch()

    @Gtk.Template.Callback()
    def _on_login_token_entry_inserted(self, *args):
        token = self._login_token_entry.get_text()
        self._login_token_entry.set_text("")
        self._save_token(token)
        self.props.application.relaunch()

    @Gtk.Template.Callback()
    def _on_notification_button_clicked(self, button):
        self._notification_revealer.set_reveal_child(False)

    def _save_token(self, token: str):
        logging.info("setting token in keyring")
        keyring.set_password("mirdorph", "token", token)
        logging.info("token set in keyring")
