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
import threading
import discord
from pathlib import Path
from gettext import gettext as _
from gi.repository import Gtk, Gio, GLib, Handy
from .confman import ConfManager
from .attachment import MessageEntryBarAttachment
from .event_receiver import EventReceiver


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/message_entry_bar.ui")
class MessageEntryBar(Gtk.Box, EventReceiver):
    __gtype_name__ = "MessageEntryBar"

    _message_entry: Gtk.Entry = Gtk.Template.Child()
    _send_button: Gtk.Button = Gtk.Template.Child()

    _attachment_togglebutton: Gtk.ToggleButton = Gtk.Template.Child()
    _attachment_area_revealer: Gtk.Revealer = Gtk.Template.Child()
    _attachment_container: Gtk.Box = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)
        self.context = context
        self.app = Gio.Application.get_default()

        self._already_displaying_user_currently_typing = False

        self._add_extra_attachment_button = MessageEntryBarAttachment(
            parent_for_sign=self, add_mode=True)
        self._add_extra_attachment_button.show()
        self._attachment_container.pack_start(self._add_extra_attachment_button, False, False, 0)

        self.app.confman.connect("setting-changed", self._on_confman_setting_changed)
        self._should_send_typing_events = self.app.confman.get_value("send_typing_events")

        threading.Thread(target=self._check_if_can_send_target).start()

    def _on_confman_setting_changed(self, confman: ConfManager, setting: str):
        self._should_send_typing_events = self.app.confman.get_value("send_typing_events")

    def handle_first_see(self):
        """
        Handle for first display, for example to focus the entry bar,
        this is meant to be called when this is first displayed, for
        example when switching to this channel
        """
        self._message_entry.grab_focus()

    async def _channel_is_sendable_to_you(self, channel: discord.abc.GuildChannel) -> bool:
        our_permissions = channel.permissions_for(
            await channel.guild.fetch_member(self.app.discord_client.user.id)
        )
        return our_permissions.send_messages

    def _check_if_can_send_target(self):
        can_send = asyncio.run_coroutine_threadsafe(
            self._channel_is_sendable_to_you(self.context.channel_disc),
            self.app.discord_loop
        ).result()
        GLib.idle_add(self._check_if_can_send_gtk_target, can_send)

    def _check_if_can_send_gtk_target(self, can_send: bool):
        if not can_send:
            self.set_sensitive(can_send)
            self._message_entry.set_placeholder_text(_("Insufficient permissions"))

    async def _message_send_wrapper(self, message: str, files: list):
        try:
            await self.context.channel_disc.send(message, files=files)
        except Exception as e:
            pass

    def _do_attempt_send(self):
        message = self._message_entry.get_text()
        # Done here, not with a separate async wrapper with idle_add
        # because it doesn't help because if we do it like that
        # and it executes in the wrong order.
        # Unsetting happens in on_message due to similar reasons
        self.context.scroll_for_msg_send = True

        atts_to_send = []
        for att_widg in self._attachment_container.get_children():
            if att_widg.add_mode:
                continue

            # Discord 10 maximum
            if len(atts_to_send) >= 10:
                break

            atts_to_send.append(
                discord.File(
                    att_widg.full_filename,
                    filename=Path(att_widg.full_filename).name
                )
            )

        asyncio.run_coroutine_threadsafe(
            self._message_send_wrapper(message, files=atts_to_send),
            self.app.discord_loop
        )

        for child in self._attachment_container.get_children():
            if not child.add_mode:
                child.destroy()
        self._attachment_togglebutton.set_active(False)
        self._message_entry.set_text("")

        self._send_button.set_sensitive(False)
        self._send_button.get_style_context().remove_class("suggested-action")

    @Gtk.Template.Callback()
    def _on_send_button_clicked(self, entry):
        self._do_attempt_send()

    @Gtk.Template.Callback()
    def _on_message_entry_activate(self, entry):
        self._do_attempt_send()

    async def _simulate_typing(self):
        # We don't want to continually spam typing events
        # and hit the rate limit
        if self._already_displaying_user_currently_typing:
            return

        self._already_displaying_user_currently_typing = True
        await self.context.channel_disc.trigger_typing()
        await asyncio.sleep(9) # Value 10 seems to be about how long it lasts
        self._already_displaying_user_currently_typing = False

    # When we send a message, the typing trigger is automatically cancelled,
    # however we don't reset currently_typing immediately, but instead
    # continue to wait the full 9 seconds. This gives a weird delay
    # for the next message.
    def disc_on_message(self, message):
        if message.author == self.context.channel_disc.guild.me:
            self._already_displaying_user_currently_typing = False

    @Gtk.Template.Callback()
    def _on_message_entry_changed(self, entry):
        if entry.get_text():
            self._send_button.set_sensitive(True)
            if self._should_send_typing_events:
                asyncio.run_coroutine_threadsafe(
                    self._simulate_typing(),
                    self.app.discord_loop
                )
            self._send_button.get_style_context().add_class("suggested-action")
        elif len(self._attachment_container.get_children()) < 2:
            self._send_button.set_sensitive(False)
            self._send_button.get_style_context().remove_class("suggested-action")

    @Gtk.Template.Callback()
    def _on_revealer_reveal_child(self, revealer, param):
        self.context.attachment_tray_scroll_mode = (
            not self._attachment_area_revealer.get_child_revealed(
            ) and self.context.is_scroll_at_bottom
        )

    @Gtk.Template.Callback()
    def _on_revealer_child_revealed(self, revealer, param):
        if self._attachment_area_revealer.get_child_revealed():
            self.context.attachment_tray_scroll_mode = False

    # Gtk Box does not support Gtk.Container::add
    def emulate_attachment_container_change(self):
        if len(self._attachment_container.get_children()) > 1:
            self._send_button.set_sensitive(True)
            self._send_button.get_style_context().add_class("suggested-action")
