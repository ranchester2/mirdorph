import discord
from .event_receiver import EventReceiver
from gi.repository import Gio, Gtk, Handy

class EventManager:
    def __init__(self):
        self.app = Gio.Application.get_default()
        self.receivers = []

    def register_receiver(self, receiver: EventReceiver):
        self.receivers.append(receiver)

    def dispatch_event(self, name: str, *args, **kwargs):
        for receiver in self.receivers:
            func = getattr(receiver, ("disc_" + name))
            func(*args, **kwargs)
