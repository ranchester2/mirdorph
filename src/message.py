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
import os
import random
import time
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Handy
from .attachment import GenericAttachment, ImageAttachment, AttachmentType, get_attachment_type

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
    _message_label: Gtk.Label = Gtk.Template.Child()

    _attachment_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, disc_message, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self._disc_message = disc_message

        # Overall unique identifier to tell duplicates apart
        # here it is a message id, however other ways are possible.
        # standard checking won't work because a message can have multiple
        # objects
        self.uniq_id = disc_message.id
        self.timestamp = disc_message.created_at.timestamp()

        # Cause we use xml markup, and some names can break that, and then
        # you have a broken label
        safe_name = self._disc_message.author.name.translate({ord(c): None for c in '"\'<>&'})
        self._username_label.set_markup(f"<b>{safe_name}</b>")

        # Message that doesn't have any spaces for a very long time can break wrapping
        # NOTE: this is now seamy useless with the new wrap_mode
        if len(self._disc_message.content) > 60 and ' ' not in self._disc_message.content:
            safe_message = "UNSAFE CONTENT: CENSORING"
            logging.warning("censoring unsafe message")
        else:
            safe_message = self._disc_message.content

        self._message_label.set_label(safe_message)

        avatar = UserMessageAvatar(self._disc_message.author, margin_top=3)
        avatar.show()
        self._avatar_box.pack_start(avatar, False, False, 0)

        # Empty messages (like when sending images) look weird otherwise
        if not self._message_label.get_label():
            self._message_label.get_parent().remove(self._message_label)

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

        label_color_fetch_thread = threading.Thread(target=self._fetch_label_color_target)
        label_color_fetch_thread.start()

    # NOTE: only call this from the non blocking thread
    def _helper_get_member(self):
        member = asyncio.run_coroutine_threadsafe(
            self._disc_message.guild.fetch_member(
                self._disc_message.author.id
            ),
            Gio.Application.get_default().discord_loop
        ).result()

        return member

    def _fetch_label_color_target(self):
        # Those with 0000 are generally "fake" members that are invalid
        if self._disc_message.author.discriminator == "0000":
            return

        member = self._disc_message.guild.get_member(self._disc_message.author.id)
        if member is None:
            # To make rate limit less frequent, we don't cache this for whatever reason,
            # get_member always fails
            time.sleep(random.uniform(0.1, 3.25))

            try:
                member = self._helper_get_member()
            except discord.errors.NotFound:
                logging.warning(f"could not get member info of {self._disc_message.author}, 404? Will retry")
                time.sleep(random.uniform(5.0, 10.0))
                logging.warning(f"retrieing for member info {self._disc_message.author}")
                try:
                    member = self._helper_get_member()
                except discord.errors.NotFound:
                    logging.warning(f"could not get even after retry, cancelling")
                    return

        top_role = member.roles[-1]
        color_formatted = '#%02x%02x%02x' % top_role.color.to_rgb()

        # @everyone is completely black, we should fix that
        color_is_indrove = (color_formatted == "#000000")

        GLib.idle_add(self._label_color_gtk_target, color_formatted, color_is_indrove)

    def _label_color_gtk_target(self, color: str, color_is_indrove: bool):
        if not color_is_indrove:
            self._username_label.set_markup(
                f"<span foreground='{color}'>{self._username_label.get_label()}</span>"
            )