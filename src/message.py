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

import random
import time
import asyncio
import logging
import threading
import discord
import os
from pathlib import Path
from xml.sax.saxutils import escape as escape_xml
from gi.repository import Adw, Gtk, GObject, Gio, GLib, Gdk, GdkPixbuf
from .event_receiver import EventReceiver
from .attachment import GenericAttachment, ImageAttachment, AttachmentType, get_attachment_type
from .message_parsing import MessageComponent, calculate_msg_parts

class MessageContent(Gtk.Box):
    def __init__(self, message_content: str, *args, **kwargs):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, *args, **kwargs)
        self._message_content = message_content
        self.exports = []

        for component in self._do_parse_construct():
            self.exports.extend(component.exports)
            self.append(component)

    def _do_parse_construct(self) -> list:
        return [
            MessageComponent(comp[1], component_type=comp[0])
            for comp in calculate_msg_parts(self._message_content)
        ]

class UserMessageAvatar(Adw.Avatar):
    __gtype_name__ = "UserMessageAvatar"

    _avatar_icon_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    def __init__(self, user: discord.User, *args, **kwargs):
        Adw.Avatar.__init__(self, size=32, text=user.name, show_initials=True, *args, **kwargs)
        self.app = Gio.Application.get_default()

        self._user_disc = user
        self._avatar_icon_path = Path(
            self._avatar_icon_dir_path / Path("user" + "_" + str(self._user_disc.id) + ".png")
        )

        #threading.Thread(target=self._fetch_avatar_target).start()

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

    def _set_avatar_gtk_target(self):
        if self._avatar_icon_path.is_file():
            try:
                image = Gtk.Image.new_from_file(
                    str(self._avatar_icon_path)
                )
                self.set_custom_image(image.get_paintable())
            except GLib.Error as e:
                logging.warning(
                    f"encountered unkown avatar error as {e}. Probably loading partially downloaded file."
                )

class MessageMobject(GObject.GObject, EventReceiver):
    """
    A representation of an object in the message data model,
    a GObject bsed on the discord message object, with special handling
    for GObject signals, username label generation, headers, and selectively
    exposes Discord attributes.
    """

    def __init__(self, disc_message: discord.Message, merged=False, is_header=False):
        """
        Create a Mobject for a discord message event.
        param:
            disc_message: the `discord.Message` of the message, if `is_header` is True, this
            should be None
            merged: if the message should originally be merged (part of a group, some things
            are then not displayed)
            is_header: is this the view header widget, done in this awkward way because all
            objects must be of the same type. Other functionality of the Mobject won't work
            as expected with this enabled
        """
        GObject.GObject.__init__(self)
        EventReceiver.__init__(self)
        self.app = Gio.Application.get_default()
        self.is_header = is_header
        if self.is_header:
            return

        self._disc_message = disc_message
        self._merged = merged
        self._username_color = None

        # Recommended attributes exposed selectively, this will
        # also allow us to handle events well
        self.content = self._disc_message.content
        self.created_at = self._disc_message.created_at
        self.author = self._disc_message.author
        self.attachments = self._disc_message.attachments
        self.channel = self._disc_message.channel
        self.guild = self._disc_message.guild
        self.id = self._disc_message.id

        # Additional "lazy" loading of properties like the username color
        # should happen in the Mobject, not the widget
        threading.Thread(target=self._fetch_label_color_target).start()

    @GObject.Property(type=bool, default=False)
    def merged(self):
        """If the message should be merged (common grouping method)"""
        return self._merged

    @merged.setter
    def merged(self, merge: bool):
        self._merged = merge

    @GObject.Property(type=str)
    def username_color(self):
        """The username color, intelligently gathered at runtime"""
        return self._username_color

    @username_color.setter
    def username_color(self, color: str):
        self._username_color = color

    def _helper_get_member(self) -> discord.Member:
        """
        Efficiently get our discord member.

        Such complication is required becaused .author isn't always one,
        and it is easy to make a lot of API calls getting one.

        NOTE: only call this from the non blocking thread

        returns:
            discord.Member - if it worked,
            None - if everything failed (sometimes happens, 404 bug)
        """
        # When we receive a message, it is a Member, however from history
        # it is a user.
        if isinstance(self.author, discord.Member):
            member = self.author
            self.app.custom_member_cache[member.id] = member
        else:
            if self.author.id in self.app.custom_member_cache:
                member = self.app.custom_member_cache[self.author.id]
            else:
                member = self.guild.get_member(self.author.id)
                if member:
                    self.app.custom_member_cache[member.id] = member
                else:
                    # Sometimes when fetching members like this it simply isn't found for
                    # seemingly no reason. Maybe it is todo with if they are online?
                    try:
                        member = asyncio.run_coroutine_threadsafe(
                            self.guild.fetch_member(
                                self.author.id
                            ),
                            self.app.discord_loop
                        ).result()
                        self.app.custom_member_cache[self.author.id] = member
                    except discord.errors.NotFound:
                        logging.warning(f"could not get member info of {self.author}, 404?")
                        return
        return member

    def _fetch_label_color_target(self):
        # Those with 0000 are generally "fake" members that are invalid
        if self.author.discriminator == "0000":
            return

        # Really needed especially with all Mobjects attempting to fetch it
        time.sleep(random.uniform(0.25, 3))

        member = self._helper_get_member()
        if member is None:
            return
        top_role = member.roles[-1]
        color_formatted = "#%02x%02x%02x" % top_role.color.to_rgb()

        # @everyone is completely black, that should be the default theme
        # color instead.
        if color_formatted == "#000000":
            return

        GLib.idle_add(self._label_color_gtk_target, color_formatted)

    def _label_color_gtk_target(self, color: str):
        self.set_property("username-color", color)


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/message.ui")
class MessageWidget(Gtk.Box):
    __gtype_name__ = "MessageWidget"

    _avatar_box: Gtk.Box = Gtk.Template.Child()

    _username_label: Gtk.Label = Gtk.Template.Child()
    _message_content_container: Adw.Bin = Gtk.Template.Child()

    _attachment_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, merged=False, *args, **kwargs):
        Gtk.ListBoxRow.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()

        # Workaround to a weird state where attachments are added, but they do not
        # count towards the box, so they are not correctly removed
        self._added_att_exp = []

    def _handle_merge(self, *args):
        if self._item.get_property("merged"):
            self.add_css_class("merged-discord-message")
            self._username_label.hide()
            if hasattr(self, "_avatar"):
                self._avatar_box.remove(self._avatar)
                del(self._avatar)
            self._avatar_box.props.width_request = 32
        else:
            self.remove_css_class("merged-discord-message")
            self._username_label.show()
            if not hasattr(self, "_avatar"):
                self._avatar = UserMessageAvatar(self._item.author, margin_top=3)
                self._avatar_box.append(self._avatar)
            self._avatar_box.props.width_request = -1

    def _handle_username_color(self, *args):
        color = self._item.get_property("username-color")
        if color:
            self._username_label.set_markup(
                f"<span foreground='{color}'>{escape_xml(self._item.author.name)}</span>"
            )

    def do_bind(self, item: MessageMobject):
        self._item = item
        self._item.connect("notify::merged", self._handle_merge)
        self._item.connect("notify::username-color", self._handle_username_color)

        self._message_content_wid = MessageContent(self._item.content)
        self._message_content_container.append(self._message_content_wid)

        self._username_label.set_label(escape_xml(self._item.author.name))
        # For initial setup if widget created after mobject already fetched
        self._handle_username_color()

        # Handling merging takes care of building the avatar if it does not exist
        self._handle_merge()

        for att in self._item.attachments:
            if get_attachment_type(att) == AttachmentType.IMAGE:
                att_widg = ImageAttachment(att, self._item.channel.id)
                att_widg.set_halign(Gtk.Align.START)
                self._added_att_exp.append(att_widg)
                self._attachment_box.append(att_widg)
            # If an attachment type is unsupported yet, it becomes generic
            else:
                att_widg = GenericAttachment(att, self._item.channel.id)
                att_widg.set_halign(Gtk.Align.START)
                self._added_att_exp.append(att_widg)
                self._attachment_box.append(att_widg)
            # There is atleast one attachment, and it looks better with a top margin,
            # not set from the start, as it looks weird with regular messages, and hiding
            # it is complicated with exports.
            self._attachment_box.set_margin_top(5)

        for export in self._message_content_wid.exports:
            self._added_att_exp.append(export)
            self._attachment_box.append(export)

    def do_unbind(self):
        self._item = None

        # Not always connected, even with handler id
        try:
            self.disconnect_by_func(self._handle_merge)
            self.disconnect_by_func(self._handle_username_color)
        except TypeError:
            pass

        for exp_att_wid in self._added_att_exp:
            if exp_att_wid in self._attachment_box:
                self._attachment_box.remove(exp_att_wid)

        if hasattr(self, "_avatar"):
            self._avatar_box.remove(self._avatar)
            del(self._avatar)

        self._username_label.set_label("")

        self._message_content_container.remove(self._message_content_wid)
        del(self._message_content_wid)
