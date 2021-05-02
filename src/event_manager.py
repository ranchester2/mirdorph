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
import logging
from .event_receiver import EventReceiver
from gi.repository import Gio, Gtk, Handy

class EventManager:
    def __init__(self):
        self.app = Gio.Application.get_default()
        self._receivers = []

    def register_receiver(self, receiver: EventReceiver):
        self._receivers.append(receiver)

    def dispatch_event(self, name: str, *args, **kwargs):
        logging.info(f"re-dispatcihing event {name} to GLib")
        for receiver in self._receivers:
            func = getattr(receiver, ("disc_" + name))
            func(*args, **kwargs)
