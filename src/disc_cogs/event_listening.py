import discord
import gi
from discord.ext import commands
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Handy, Gio, GLib

class EventListeningDispatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        print(message.content)

def setup(bot: commands.Bot):
    bot.add_cog(EventListeningDispatcher(bot))
