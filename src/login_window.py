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
from gi.repository import Gtk, Gdk, GLib, Handy

# Needs to be custom because GDK_IS_WAYLAND_DISPLAY seems to only exist
# in C and isn't really documented, just appears once in a random blog post
def check_if_wayland() -> bool:
    display = Gdk.Display.get_default()
    if "wayland" in display.get_name().lower():
        return True
    else:
        if "XDG_SESSION_TYPE" in os.environ:
            return os.environ["XDG_SESSION_TYPE"] == "wayland"

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/login_window.ui')
class MirdorphLoginWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'MirdorphLoginWindow'

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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
        # Discordlogin doesn't work properly on X11 for some reason
        if not check_if_wayland():
            wayland_only_dialog = Gtk.MessageDialog(
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.CLOSE,
                text="Graphical login is not supported on the X11 windowing system",
                secondary_text="""\
Graphical login is only supported on Wayland, if you cannot use Wayland, use the \
advanced 'Manual Token' method instead."""
            )
            wayland_only_dialog.set_transient_for(self)
            wayland_only_dialog.run()
            wayland_only_dialog.destroy()
        else:
            self.set_sensitive(False)
            token_web_retrieval_thread = threading.Thread(target=self._token_web_retrieval_target)
            token_web_retrieval_thread.start()

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
            self._relaunch()

    def _token_web_retrieval_target(self):
        token = subprocess.check_output('discordlogin', shell=True, text=True)
        GLib.idle_add(self._token_generic_retrieval_gtk_target, token)

    def _token_generic_retrieval_gtk_target(self, token):
        if token:
            self._save_token(token)
        self._relaunch()

    @Gtk.Template.Callback()
    def _on_login_token_entry_inserted(self, *args):
        token = self._login_token_entry.get_text()
        self._login_token_entry.set_text("")
        self._save_token(token)
        self._relaunch()

    def _save_token(self, token: str):
        logging.info("setting token in keyring")
        keyring.set_password("mirdorph", "token", token)
        logging.info("token set in keyring")

    def _relaunch(self):
        logging.info("launching program duplicate instance")
        os.execv(sys.argv[0], sys.argv)
        logging.info("exiting initial program")
        os._exit(1)
