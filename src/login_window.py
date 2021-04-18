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
from gi.repository import Gtk, Handy


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/login_window.ui')
class MirdorphLoginWindow(Handy.ApplicationWindow):
    __gtype_name__ = 'MirdorphLoginWindow'

    login_page_deck = Gtk.Template.Child()
    login_welcome_page = Gtk.Template.Child()
    login_token_page = Gtk.Template.Child()

    login_token_entry = Gtk.Template.Child()
    login_token_entry_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def on_token_button_clicked(self, button):
        self.login_page_deck.set_visible_child(self.login_token_page)

    @Gtk.Template.Callback()
    def on_main_cancel_button_clicked(self, button):
        os._exit(1)

    @Gtk.Template.Callback()
    def on_login_token_entry_changed(self, entry):
        self.login_token_entry_button.get_style_context().add_class("suggested-action")

    @Gtk.Template.Callback()
    def on_login_token_entry_inserted(self, *args):
        token = self.login_token_entry.get_text()
        self.login_token_entry.set_text("")
        logging.info("setting token in keyring")
        keyring.set_password("mirdorph", "token", token)
        logging.info("token set in keyring")
        logging.info("launching program duplicate instance")
        os.execv(sys.argv[0], sys.argv)
        logging.info("exiting initial program")
        os._exit(1)        
