import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '1')
from gi.repository import Gtk, Handy, Gio, GLib
import discord
from discord.ext import commands


class EventListeningDispatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def forward_event(self, name, *args, **kwargs):
        app = Gio.Application.get_default()
        app.event_manager.dispatch_event(name, *args, **kwargs)

    # Could be minimized with exec(), but that would be insane

    @commands.Cog.listener()
    async def on_connect(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_connect", *args, **kwargs)

    @commands.Cog.listener()
    async def on_shard_connect(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_shard_connect", *args, **kwargs)

    @commands.Cog.listener()
    async def on_disconnect(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_disconnect", *args, **kwargs)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_shard_disconnect", *args, **kwargs)

    @commands.Cog.listener()
    async def on_ready(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_ready", *args, **kwargs)

    @commands.Cog.listener()
    async def on_shard_ready(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_shard_ready", *args, **kwargs)

    @commands.Cog.listener()
    async def on_resumed(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_resumed", *args, **kwargs)

    @commands.Cog.listener()
    async def on_shard_resumed(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_shard_resumed", *args, **kwargs)

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_error", *args, **kwargs)

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_socket_raw_receive", *args, **kwargs)

    @commands.Cog.listener()
    async def on_socket_raw_send(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_socket_raw_send", *args, **kwargs)

    @commands.Cog.listener()
    async def on_typing(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_typing", *args, **kwargs)

    @commands.Cog.listener()
    async def on_message(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_message", *args, **kwargs)

    @commands.Cog.listener()
    async def on_message_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_message_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_bulk_message_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_message_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_message_edit(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_message_edit", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_message_edit", *args, **kwargs)

    @commands.Cog.listener()
    async def on_reaction_add(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_reaction_add", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_reaction_add", *args, **kwargs)

    @commands.Cog.listener()
    async def on_reaction_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_reaction_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_reaction_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_reaction_clear(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_reaction_clear", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_reaction_clear", *args, **kwargs)

    @commands.Cog.listener()
    async def on_reaction_clear_emoji(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_reaction_clear_emoji", *args, **kwargs)

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_raw_reaction_clear_emoji", *args, **kwargs)

    @commands.Cog.listener()
    async def on_private_channel_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_private_channel_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_private_channel_create(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_private_channel_create", *args, **kwargs)

    @commands.Cog.listener()
    async def on_private_channel_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_private_channel_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_private_channel_pins_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_private_channel_pins_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_channel_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_channel_create", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_channel_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_channel_pins_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_integrations_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_webhooks_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_webhooks_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_member_join(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_member_join", *args, **kwargs)

    @commands.Cog.listener()
    async def on_member_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_member_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_member_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_member_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_user_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_user_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_join(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_guild_join", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_guild_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_guild_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_role_create(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_role_create", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_role_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_role_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_role_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_emojis_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_available(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_available", *args, **kwargs)

    @commands.Cog.listener()
    async def on_guild_unavailable(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_guild_unavailable", *args, **kwargs)

    @commands.Cog.listener()
    async def on_voice_state_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_voice_state_update", *args, **kwargs)

    @commands.Cog.listener()
    async def on_member_ban(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_member_ban", *args, **kwargs)

    @commands.Cog.listener()
    async def on_member_unban(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_member_unban", *args, **kwargs)

    @commands.Cog.listener()
    async def on_invite_create(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_invite_create", *args, **kwargs)

    @commands.Cog.listener()
    async def on_invite_delete(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_invite_delete", *args, **kwargs)

    @commands.Cog.listener()
    async def on_group_join(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_group_join", *args, **kwargs)

    @commands.Cog.listener()
    async def on_group_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event, "on_group_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_relationship_add(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_relationship_add", *args, **kwargs)

    @commands.Cog.listener()
    async def on_relationship_remove(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_relationship_remove", *args, **kwargs)

    @commands.Cog.listener()
    async def on_relationship_update(self, *args, **kwargs):
        GLib.idle_add(self.forward_event,
                      "on_relationship_update", *args, **kwargs)


def setup(bot: commands.Bot):
    bot.add_cog(EventListeningDispatcher(bot))
