import discord
import gi
from discord.ext import commands
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Handy, Gio, GLib

class EventListeningDispatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def forward_event(self, name, *args):
        app = Gio.Application.get_default()
        app.event_manager.dispatch_event(name, *args)

    @commands.Cog.listener()
    async def on_message(self, message):
        GLib.idle_add(self.forward_event, "on_message", message)


def setup(bot: commands.Bot):
    bot.add_cog(EventListeningDispatcher(bot))
