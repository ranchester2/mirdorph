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
import logging
import threading
import discord
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Gdk, Handy
from .attachment import MessageEntryBarAttachment


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message_entry_bar.ui')
class MessageEntryBar(Gtk.Box):
    __gtype_name__ = "MessageEntryBar"

    _message_entry = Gtk.Template.Child()
    _send_button = Gtk.Template.Child()

    _attachment_togglebutton = Gtk.Template.Child()
    _attachment_area_revealer = Gtk.Template.Child()
    _attachment_container = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)

        self.context = context
        self.app = Gio.Application.get_default()

        # Read comment there about why parent_for_sign
        self._add_extra_attachment_button = MessageEntryBarAttachment(parent_for_sign=self, add_mode=True)
        self._add_extra_attachment_button.show()
        self._attachment_container.pack_start(self._add_extra_attachment_button, False, False, 0)

        check_if_can_send_thread = threading.Thread(target=self._check_if_can_send_target)
        check_if_can_send_thread.start()

    def handle_first_see(self):
        """
        To act as if being seen again for the first time.

        This is for example if the context has just bene opened, or if just popped out.
        """
        self._message_entry.grab_focus()

    def _check_if_can_send_target(self):
        can_send = asyncio.run_coroutine_threadsafe(
            self._channel_is_sendable_to_you(self.context.channel_disc),
            self.app.discord_loop
        ).result()
        GLib.idle_add(self._check_if_can_send_gtk_target, can_send)

    def _check_if_can_send_gtk_target(self, can_send: bool):
        if not can_send:
            self.set_sensitive(can_send)
            self._message_entry.set_placeholder_text("Insufficient permissions")

    async def _channel_is_sendable_to_you(self, channel: discord.abc.GuildChannel) -> bool:
        our_permissions = channel.permissions_for(
            await channel.guild.fetch_member(self.app.discord_client.user.id)
        )
        return our_permissions.send_messages

    async def _message_send_wrapper(self, message: str, files: list):
        try:
            await self.context.channel_disc.send(message, files=files)
        except Exception as e:
            GLib.idle_add(lambda msg_error : self.app.do_error("Failure sending message", str(msg_error)), e)

    def _do_attempt_send(self):
        message = self._message_entry.get_text()
        # Done here, not with a separate async wrapper with idle_add
        # because it doesn't help because if we do it from that
        # it executes in the wrong order.

        # However now it may be a bit different with the fractal scrolling
        # like system.

        # Unsetting happens in on_message due to similar reasons
        self.context.prepare_scroll_for_msg_send()

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
        self._message_entry.set_text('')

        # This doesn't really work with when attachments are sent too,
        # so we do this again manually here
        self._send_button.set_sensitive(False)
        self._send_button.get_style_context().remove_class("suggested-action")

    @Gtk.Template.Callback()
    def _on_send_button_clicked(self, entry):
        self._do_attempt_send()
        
    @Gtk.Template.Callback()
    def _on_message_entry_activate(self, entry):
        self._do_attempt_send()

    @Gtk.Template.Callback()
    def _on_message_entry_changed(self, entry):
        if entry.get_text():
            self._send_button.set_sensitive(True)
            self._send_button.get_style_context().add_class("suggested-action")
        elif len(self._attachment_container.get_children()) < 2:
            self._send_button.set_sensitive(False)
            self._send_button.get_style_context().remove_class("suggested-action")

    @Gtk.Template.Callback()
    def _on_revealer_reveal_child(self, revealer, param):
        if not self._attachment_area_revealer.get_child_revealed() and self.context.precise_is_scroll_at_bottom:
           self.context.start_attachment_reveal_scroll_mode()
        else:
           self.context.end_attachment_reveal_scroll_mode()

    @Gtk.Template.Callback()
    def _on_revealer_child_revealed(self, revealer, param):
        if self._attachment_area_revealer.get_child_revealed():
            self.context.end_attachment_reveal_scroll_mode()

    # Gtk Box does not support this, so we will do it manually when we add
    def emulate_attachment_container_change(self):
        if len(self._attachment_container.get_children()) > 1:
            self._send_button.set_sensitive(True)
            self._send_button.get_style_context().add_class("suggested-action")
