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
from gi.repository import Gio, Gtk, Handy


class EventReceiver:
    """
    An object used to receive Discord events

    To use, subclass it and init it.
    Then on functions "disc_" + event name from documentation
    you can receive events and all the arguments
    """
    
    def __init__(self):
        self._ev_app = Gio.Application.get_default()
        self._ev_app.event_manager.register_receiver(self)

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
