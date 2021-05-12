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

import asyncio
import datetime
import logging
import threading
import discord
from gi.repository import Gtk, Gio, GLib, Gdk, Handy
from .event_receiver import EventReceiver

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_properties_window.ui')
class ChannelPropertiesWindow(Handy.Window, EventReceiver):
    __gtype_name__ = "ChannelPropertiesWindow"

    _channel_avatar: Handy.Avatar = Gtk.Template.Child()

    _name_label: Gtk.Label = Gtk.Template.Child()
    _description_label: Gtk.Label = Gtk.Template.Child()

    _last_activity_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel: discord.TextChannel, *args, **kwargs):
        Handy.Window.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self.app = Gio.Application.get_default()

        self._channel_disc = channel

        self._name_label.set_label("#" + self._channel_disc.name)
        self._channel_avatar.set_text(self._channel_disc.name)
        if self._channel_disc.topic:
            cleaned_topic = self._channel_disc.topic.replace("\n", "")
            self._description_label.set_label(cleaned_topic)
        else:
            self._description_label.destroy()

        last_activity_time_thread = threading.Thread(target=self._get_last_activity_time_target)
        last_activity_time_thread.start()

    async def _get_last_activity_time_async_target(self, channel: discord.TextChannel) -> datetime.datetime:
        async for message in channel.history(limit=1):
            return message.created_at

    def _get_last_activity_time_target(self):
        last_activity_time = asyncio.run_coroutine_threadsafe(
            self._get_last_activity_time_async_target(self._channel_disc),
            self.app.discord_loop
        ).result()

        GLib.idle_add(self._set_last_activity_gtk_target, last_activity_time)

    def _set_last_activity_gtk_target(self, time: datetime.datetime):
        readable_time = time.strftime("%a. %dd. %Hh. %Mm.")
        self._last_activity_button.set_label(readable_time)

    @Gtk.Template.Callback()
    def _on_last_activity_button_activate(self, button):
        time = self._last_activity_button.get_label()
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(time, -1)

    @Gtk.Template.Callback()
    def _on_statistics_button_activate(self, button):
        raise NotImplementedError

