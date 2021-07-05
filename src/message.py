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
from pathlib import Path
from xml.sax.saxutils import escape as escape_xml
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Handy
from .attachment import GenericAttachment, ImageAttachment, AttachmentType, get_attachment_type
from .message_parsing import MessageComponent, calculate_msg_parts

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
        self.app = Gio.Application.get_default()

        self._user_disc = user
        self._avatar_icon_path = Path(
            self._avatar_icon_dir_path / Path("user" + "_" + str(self._user_disc.id) + ".png")
        )

        threading.Thread(target=self._fetch_avatar_target).start()

    def _fetch_avatar_target(self):
        avatar_asset = self._user_disc.avatar_url_as(size=1024, format="png")

        # Unlike with guilds, we will have many, many things attempting to download
        # and save it there, which causes weird errors due to incomplete save while
        # the other is loading.
        # This is a KNOWN BUG, can be mitigated by sleeping a random amount before,
        # however that ruins the user experience a lot.
        # I think the real solution in the future is to have a global avatar lock.
        if not self._avatar_icon_path.is_file():
            asyncio.run_coroutine_threadsafe(
                avatar_asset.save(str(self._avatar_icon_path)),
                self.app.discord_loop
            ).result()

        GLib.idle_add(self._set_avatar_gtk_target)

    def _load_image_func(self, size):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(self._avatar_icon_path),
                width=size,
                height=size,
                preserve_aspect_ratio=False
            )
        except GLib.Error as e:
            logging.warning(
                f"encountered unkown avatar error as {e}. Probably loading partially downloaded file."
            )
            pixbuf = None
        return pixbuf

    def _set_avatar_gtk_target(self):
        if self._avatar_icon_path.is_file():
            self.set_image_load_func(self._load_image_func)

class UsernameLabel(Gtk.Label):
    __gtype_name__ = "UsernameLabel"

    def __init__(self, author: discord.abc.User, guild: discord.Guild, *args, **kwargs):
        Gtk.Label.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._author = author
        self._guild = guild

        self.set_use_markup(True)
        self.set_xalign(0.0)
        self.get_style_context().add_class("username")

        self.set_label(escape_xml(self._author.name))

        threading.Thread(target=self._fetch_label_color_target).start()

    # NOTE: only call this from the non blocking thread
    def _helper_get_member(self) -> discord.Member:
        """
        Efficiently get our discord member.

        Such complication is required becaused .author isn't always one,
        and it is easy to make a lot of API calls getting one.

        returns:
            discord.Member - if it worked,
            None - if everything failed (sometimes happens, 404 bug)
        """
        # When we receive a message, it is a Member, however from history
        # it is a user.
        if isinstance(self._author, discord.Member):
            member = self._author
            self.app.custom_member_cache[member.id] = member
        else:
            if self._author.id in self.app.custom_member_cache:
                member = self.app.custom_member_cache[self._author.id]
            else:
                member = self._guild.get_member(self._author.id)
                if member:
                    self.app.custom_member_cache[member.id] = member
                else:
                    # Sometimes when fetching members like this it simply isn't found for
                    # seemingly no reason. Maybe it is todo with if they are online?
                    try:
                        member = asyncio.run_coroutine_threadsafe(
                            self._guild.fetch_member(
                                self._author.id
                            ),
                            self.app.discord_loop
                        ).result()
                        self.app.custom_member_cache[self._author.id] = member
                    except discord.errors.NotFound:
                        logging.warning(f"could not get member info of {self._author}, 404?")
                        return
        return member

    def _fetch_label_color_target(self):
        # Those with 0000 are generally "fake" members that are invalid
        if self._author.discriminator == "0000":
            return

        member = self._helper_get_member()
        if member is None:
            return
        top_role = member.roles[-1]
        color_formatted = "#%02x%02x%02x" % top_role.color.to_rgb()

        # @everyone is completely black, we should fix that, to be the default
        # theme color instead
        color_is_default = (color_formatted == "#000000")

        GLib.idle_add(self._label_color_gtk_target, color_formatted, color_is_default)

    def _label_color_gtk_target(self, color: str, color_is_default: bool):
        if not color_is_default:
            self.set_markup(
                f"<span foreground='{color}'>{escape_xml(self._author.name)}</span>"
            )

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/message.ui")
class MirdorphMessage(Gtk.ListBoxRow):
    __gtype_name__ = "MirdorphMessage"

    _avatar_box: Gtk.Box = Gtk.Template.Child()

    _username_container: Gtk.Box = Gtk.Template.Child()
    _message_content_container: Gtk.Bin = Gtk.Template.Child()

    _attachment_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, disc_message, merged=False, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._disc_message = disc_message
        self.merged = merged
        # It can be needed to check the author of already existing
        # messages. For example, when adding a message to check
        # if the previous message is from the same user.
        self.author: discord.abc.User = self._disc_message.author

        # Basically shows that this corresponds to a specific
        # Discord event. Can be used to avoid constructing duplicates,
        # for example check if a widget based on a message is already created.
        self.disc_id = disc_message.id

        # Very useful for sorting
        self.timestamp = disc_message.created_at.timestamp()

        self._message_content_wid = MessageContent(self._disc_message.content)
        self._message_content_wid.show()
        self._message_content_container.pack_start(self._message_content_wid, False, False, 0)

        if self.merged:
            self.merge()
        else:
            # Unmerging also builds all of the widgets that are only constructed
            # if the message isn't merged.
            self.unmerge()

        for att in self._disc_message.attachments:
            if get_attachment_type(att) == AttachmentType.IMAGE:
                att_widg = ImageAttachment(att, self._disc_message.channel.id)
                att_widg.set_halign(Gtk.Align.START)
                att_widg.show()
                self._attachment_box.pack_start(att_widg, False, False, 0)
            # If an attachment type is unsupported yet, it becomes generic
            else:
                att_widg = GenericAttachment(att, self._disc_message.channel.id)
                att_widg.set_halign(Gtk.Align.START)
                att_widg.show()
                self._attachment_box.pack_start(att_widg, False, False, 0)
            # There is atleast one attachment, and it looks better with a top margin,
            # not set from the start, as it looks weird with regular messages, and hiding
            # it is complicated with exports.
            self._attachment_box.set_margin_top(5)

        for export in self._message_content_wid.exports:
            export.show()
            self._attachment_box.pack_start(export, False, False, 0)

    def merge(self):
        # Width = Avatar Size (32)
        self._avatar_box.props.width_request = 32
        self.get_style_context().add_class("merged-discord-message")

        if hasattr(self, "_username_label"):
            self._username_container.remove(self._username_label)
            del(self._username_label)
        if hasattr(self, "_avatar"):
            self._avatar_box.remove(self._avatar)
            del(self._avatar)
        self.merged = True

    def unmerge(self):
        self._avatar_box.props.width_request = -1
        self.get_style_context().remove_class("merged-discord-message")

        if not hasattr(self, "_username_label"):
            self._username_label = UsernameLabel(self.author, self._disc_message.guild)
            self._username_label.show()
            self._username_container.add(self._username_label)

        if not hasattr(self, "_avatar"):
            self._avatar = UserMessageAvatar(self.author, margin_top=3)
            self._avatar.show()
            self._avatar_box.pack_start(self._avatar, False, False, 0)
        self.merged = False
