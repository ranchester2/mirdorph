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

import discord
import time
import threading
import datetime
from gettext import gettext as _
from gi.repository import Gtk, GLib
from xml.sax.saxutils import escape as escape_xml
from .event_receiver import EventReceiver


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/typing_indicator.ui")
class TypingIndicator(Gtk.Revealer, EventReceiver):
    __gtype_name__ = "TypingIndicator"

    _typing_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, channel: discord.channel.TextChannel, *args, **kwargs):
        Gtk.Revealer.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self._channel = channel

        self._currently_typing_users = []
        # Basically saving when the last typing event was received,
        # so we know when to stop displaying it.
        self._times_of_user_typings = []

    def _wating_for_type_end_target(self, user: discord.User, when: datetime.datetime):
        # Even if we wanted this to be smaller, we can't decrease it too much as discord itself
        # only sends the typing event every so often.
        time.sleep(10)
        for tims in [typing_event[1] for typing_event in self._times_of_user_typings if typing_event[0] == user]:
            if tims > when:
                return

        if user in self._currently_typing_users:
            self._currently_typing_users.remove(user)
            GLib.idle_add(self._sync_typing_label)

    def _sync_typing_label(self):
        if self._currently_typing_users:
            self.set_reveal_child(True)
            if len(self._currently_typing_users) >= 2:
                typing_info_message = "are typing..."
            else:
                typing_info_message = "is typing..."
            username_list = ", ".join(
                [f"<b>{escape_xml(user.name)}</b>" for user in self._currently_typing_users]
            )
            typing_info_message = username_list + " " + typing_info_message
            self._typing_label.set_markup(typing_info_message)
        else:
            self.set_reveal_child(False)
            self._typing_label.set_label("Noone is typing.")

    def disc_on_message(self, message: discord.Message):
        print(_("Hello Translated World"))
        if message.channel == self._channel and message.author in self._currently_typing_users:
            self._currently_typing_users.remove(message.author)
            self._sync_typing_label()

    def disc_on_typing(self, channel: discord.channel.TextChannel, user: discord.User, when: datetime.datetime):
        if user == self._channel.guild.me:
            return

        if channel.id == self._channel.id:
            if user not in self._currently_typing_users:
                self._currently_typing_users.append(user)
                self._sync_typing_label()
            self._times_of_user_typings.append((user, when))
            threading.Thread(target=self._wating_for_type_end_target, args=(user, when)).start()
