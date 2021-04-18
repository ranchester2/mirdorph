import discord
from gi.repository import Gio, Gtk, Handy

class EventReceiver:
    def __init__(self):
        self.app = Gio.Application.get_default()
        self.app.event_manager.register_receiver(self)

    def disc_on_message(self, message: discord.Message):
        pass
