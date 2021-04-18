import discord
from gi.repository import Gio, Gtk, Handy


class EventReceiver:
    def __init__(self):
        self.app = Gio.Application.get_default()
        self.app.event_manager.register_receiver(self)

    def disc_on_connect(self, *args, **kwargs):
        pass

    def disc_on_shard_connect(self, *args, **kwargs):
        pass

    def disc_on_disconnect(self, *args, **kwargs):
        pass

    def disc_on_shard_disconnect(self, *args, **kwargs):
        pass

    def disc_on_ready(self, *args, **kwargs):
        pass

    def disc_on_shard_ready(self, *args, **kwargs):
        pass

    def disc_on_resumed(self, *args, **kwargs):
        pass

    def disc_on_shard_resumed(self, *args, **kwargs):
        pass

    def disc_on_error(self, event, *args, **kwargs):
        pass

    def disc_on_socket_raw_receive(self, *args, **kwargs):
        pass

    def disc_on_socket_raw_send(self, *args, **kwargs):
        pass

    def disc_on_typing(self, *args, **kwargs):
        pass

    def disc_on_message(self, *args, **kwargs):
        pass

    def disc_on_message_delete(self, *args, **kwargs):
        pass

    def disc_on_bulk_message_delete(self, *args, **kwargs):
        pass

    def disc_on_raw_message_delete(self, *args, **kwargs):
        pass

    def disc_on_message_edit(self, *args, **kwargs):
        pass

    def disc_on_raw_message_edit(self, *args, **kwargs):
        pass

    def disc_on_reaction_add(self, *args, **kwargs):
        pass

    def disc_on_raw_reaction_add(self, *args, **kwargs):
        pass

    def disc_on_reaction_remove(self, *args, **kwargs):
        pass

    def disc_on_raw_reaction_remove(self, *args, **kwargs):
        pass

    def disc_on_reaction_clear(self, *args, **kwargs):
        pass

    def disc_on_raw_reaction_clear(self, *args, **kwargs):
        pass

    def disc_on_reaction_clear_emoji(self, *args, **kwargs):
        pass

    def disc_on_raw_reaction_clear_emoji(self, *args, **kwargs):
        pass

    def disc_on_private_channel_delete(self, *args, **kwargs):
        pass

    def disc_on_private_channel_create(self, *args, **kwargs):
        pass

    def disc_on_private_channel_update(self, *args, **kwargs):
        pass

    def disc_on_private_channel_pins_update(self, *args, **kwargs):
        pass

    def disc_on_guild_channel_delete(self, *args, **kwargs):
        pass

    def disc_on_guild_channel_create(self, *args, **kwargs):
        pass

    def disc_on_guild_channel_update(self, *args, **kwargs):
        pass

    def disc_on_guild_channel_pins_update(self, *args, **kwargs):
        pass

    def disc_on_guild_integrations_update(self, *args, **kwargs):
        pass

    def disc_on_webhooks_update(self, *args, **kwargs):
        pass

    def disc_on_member_join(self, *args, **kwargs):
        pass

    def disc_on_member_remove(self, *args, **kwargs):
        pass

    def disc_on_member_update(self, *args, **kwargs):
        pass

    def disc_on_user_update(self, *args, **kwargs):
        pass

    def disc_on_guild_join(self, *args, **kwargs):
        pass

    def disc_on_guild_remove(self, *args, **kwargs):
        pass

    def disc_on_guild_update(self, *args, **kwargs):
        pass

    def disc_on_guild_role_create(self, *args, **kwargs):
        pass

    def disc_on_guild_role_delete(self, *args, **kwargs):
        pass

    def disc_on_guild_role_update(self, *args, **kwargs):
        pass

    def disc_on_guild_emojis_update(self, *args, **kwargs):
        pass

    def disc_on_guild_available(self, *args, **kwargs):
        pass

    def disc_on_guild_unavailable(self, *args, **kwargs):
        pass

    def disc_on_voice_state_update(self, *args, **kwargs):
        pass

    def disc_on_member_ban(self, *args, **kwargs):
        pass

    def disc_on_member_unban(self, *args, **kwargs):
        pass

    def disc_on_invite_create(self, *args, **kwargs):
        pass

    def disc_on_invite_delete(self, *args, **kwargs):
        pass

    def disc_on_group_join(self, *args, **kwargs):
        pass

    def disc_on_group_remove(self, *args, **kwargs):
        pass

    def disc_on_relationship_add(self, *args, **kwargs):
        pass

    def disc_on_relationship_remove(self, *args, **kwargs):
        pass

    def disc_on_relationship_update(self, *args, **kwargs):
        pass
