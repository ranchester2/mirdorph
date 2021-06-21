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
import copy
import os
import random
import time
from pathlib import Path
from enum import Enum
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Handy
from .attachment import GenericAttachment, ImageAttachment, AttachmentType, get_attachment_type
from .message_parsing import MessageComponent, ComponentType, calculate_msg_parts

class MessageContent(Gtk.Box):
    def __init__(self, message_content: str, *args, **kwargs):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self._message_content = message_content
        self.exports = []

        for component in self._do_parse_construct():
            self.exports.extend(component.exports)
            component.show()
            self.pack_start(component, False, False, 0)

    def _do_parse_construct(self) -> list:
        return [
            MessageComponent(comp[1], component_type=comp[0])
            for comp in calculate_msg_parts(self._message_content)
        ]

class UserMessageAvatar(Handy.Avatar):
    __gtype_name__ = "UserMessageAvatar"

    _avatar_icon_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    def __init__(self, user: discord.User, *args, **kwargs):
        Handy.Avatar.__init__(self, size=32, text=user.name, show_initials=True, *args, **kwargs)

        self._user_disc = user
        self._avatar_icon_path = self._get_avatar_path_from_user_id(self._user_disc.id)

        fetch_avatar_thread = threading.Thread(target=self._fetch_avatar_target)
        fetch_avatar_thread.start()

    def _get_avatar_path_from_user_id(self, user_id) -> Path:
        return Path(self._avatar_icon_dir_path / Path("user" + "_" + str(user_id) + ".png"))

    async def _save_avatar_icon(self, asset):
        await asset.save(str(self._avatar_icon_path))

    def _fetch_avatar_target(self):
        avatar_asset = self._user_disc.avatar_url_as(size=1024, format="png")

        # Unlike with guilds, we will have many, many things attempting to download
        # and save it there, which causes weird errors
        # We don't lose to much by doing this aside from having to clear cache to
        # see new image
        if not self._avatar_icon_path.is_file():
            asyncio.run_coroutine_threadsafe(
                self._save_avatar_icon(
                    avatar_asset
                ),
                Gio.Application.get_default().discord_loop
            ).result()

        # So that they don't try to load all at the same time from the same file
        time.sleep(random.uniform(0.25, 5.0)),

        GLib.idle_add(self._set_avatar_gtk_target)

    def _set_avatar_gtk_target(self):
        if self._avatar_icon_path.is_file():
            self.set_image_load_func(self._load_image_func)

    def _load_image_func(self, size):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(self._avatar_icon_path),
                width=size,
                height=size,
                preserve_aspect_ratio=False
            )
        except GLib.Error as e:
            logging.warning(f"encountered unkown avatar error as {e}")
            pixbuf = None
        return pixbuf


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message.ui')
class MirdorphMessage(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphMessage"

    _avatar_box: Gtk.Box = Gtk.Template.Child()

    _username_label: Gtk.Label = Gtk.Template.Child()
    _message_content_container: Gtk.Bin = Gtk.Template.Child()

    _attachment_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, disc_message, merged=False, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self._disc_message = disc_message
        # It can be needed to check the author of already existing
        # messages. For example, when adding a message to check
        # if the previous message is from the same user.
        self.author: discord.abc.User = self._disc_message.author

        # Overall unique identifier to tell duplicates apart
        # here it is a message id, however other ways are possible.
        # standard checking won't work because a message can have multiple
        # objects
        self.uniq_id = disc_message.id
        self.timestamp = disc_message.created_at.timestamp()

        self._username_label.set_label(self.author.name)

        self._message_content_wid = MessageContent(self._disc_message.content)
        self._message_content_wid.show()
        self._message_content_container.pack_start(self._message_content_wid, True, True, 0)

        avatar = UserMessageAvatar(self.author, margin_top=3)
        avatar.show()
        self._avatar_box.pack_start(avatar, False, False, 0)

        for att in self._disc_message.attachments:
            if get_attachment_type(att) == AttachmentType.IMAGE:
                att_widg = ImageAttachment(att)
                att_widg.set_halign(Gtk.Align.START)
                att_widg.show()
                self._attachment_box.pack_start(att_widg, True, True, 0)
            elif get_attachment_type(att) == AttachmentType.GENERIC:
                att_widg = GenericAttachment(att)
                att_widg.set_halign(Gtk.Align.START)
                att_widg.show()
                self._attachment_box.pack_start(att_widg, True, True, 0)

        for export in self._message_content_wid.exports:
            export.show()
            self._attachment_box.pack_start(export, True, True, 0)

        if merged:
            self._username_label.hide()

            # Width = Avatar Size (32)
            self._avatar_box.props.width_request = 32
            avatar.hide()

            self.get_style_context().add_class("merged-discord-message")

            return

        label_color_fetch_thread = threading.Thread(target=self._fetch_label_color_target)
        label_color_fetch_thread.start()

    # NOTE: only call this from the non blocking thread
    def _helper_get_member(self):
        member = asyncio.run_coroutine_threadsafe(
            self._disc_message.guild.fetch_member(
                self.author.id
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        return member

    def _fetch_label_color_target(self):
        # Those with 0000 are generally "fake" members that are invalid
        if self.author.discriminator == "0000":
            return

        member = self._disc_message.guild.get_member(self.author.id)
        if member is None:
            # To make rate limit less frequent, we don't cache this for whatever reason,
            # get_member always fails
            time.sleep(random.uniform(0.1, 3.25))

            try:
                member = self._helper_get_member()
            except discord.errors.NotFound:
                logging.warning(f"could not get member info of {self.author}, 404? Will retry")
                time.sleep(random.uniform(5.0, 10.0))
                logging.warning(f"retrieing for member info {self.author}")
                try:
                    member = self._helper_get_member()
                except discord.errors.NotFound:
                    logging.warning(f"could not get even after retry, cancelling")
                    return

        top_role = member.roles[-1]
        color_formatted = '#%02x%02x%02x' % top_role.color.to_rgb()

        # @everyone is completely black, we should fix that, to be the default
        # theme color instead
        color_is_indrove = (color_formatted == "#000000")

        GLib.idle_add(self._label_color_gtk_target, color_formatted, color_is_indrove)

    def _label_color_gtk_target(self, color: str, color_is_indrove: bool):
        if not color_is_indrove:
            # For XML markup
            safe_name = self._disc_message.author.name.translate({ord(c): None for c in '"\'<>&'})
            self._username_label.set_markup(
                f"<span foreground='{color}'>{safe_name}</span>"
            )
