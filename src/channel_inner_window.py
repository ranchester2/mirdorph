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
import time
import random
import sys
import subprocess
from enum import Enum
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Pango, Handy
from .event_receiver import EventReceiver
from .channel_properties_window import ChannelPropertiesWindow
from .atkpicture import AtkPicture


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_inner_window.ui')
class ChannelInnerWindow(Gtk.Box):
    __gtype_name__ = "ChannelInnerWindow"

    _context_headerbar: Handy.HeaderBar = Gtk.Template.Child()

    _toplevel_empty_stack: Gtk.Stack = Gtk.Template.Child()
    _empty_status_page: Handy.StatusPage = Gtk.Template.Child()

    _content_box: Gtk.Box = Gtk.Template.Child()

    _popout_button_stack: Gtk.Stack = Gtk.Template.Child()
    _popout_button: Gtk.Button = Gtk.Template.Child()
    _popin_button: Gtk.Button = Gtk.Template.Child()

    _context_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    _context_menu_popover: Gtk.PopoverMenu = Gtk.Template.Child()

    _flap_toggle_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel=None, empty=True, *args, **kwargs):
        """
        Create a new ChannelInnerWindow. NOTE: don't use this, use
        that of your application instead.

        param:
            channel: channel id that this context uses (note: if none empty is on)
            empty: if this is just an empty state for its status message
        """
        
        Gtk.Box.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self.channel_id = channel
        self.empty = empty
        if self.channel_id is None:
            self.empty = True

        self.is_poped = False

        if not self.empty:
            # Blocking
            self.channel_disc = asyncio.run_coroutine_threadsafe(
                self.app.discord_client.fetch_channel(self.channel_id),
                self.app.discord_loop
            ).result()

            self._context_headerbar.set_title("#" + self.channel_disc.name)
            if self.channel_disc.topic is not None:
                self._context_headerbar.set_subtitle(self.channel_disc.topic)

            self._message_view = MessageView(context=self)
            self._message_view.build_scroll()
            self._message_view.show()

            self._loading_history = False

            self._content_box.pack_start(self._message_view, True, True, 0)

            self._message_entry_bar = MessageEntryBar(context=self)
            self._message_entry_bar.show()

            self._msg_sending_scrl_mode_en = False

            self._content_box.pack_end(self._message_entry_bar, False, False, 0)
            self._content_box.pack_end(Gtk.Separator(visible=True), False, False, 0)

            self._context_action_group = Gio.SimpleActionGroup()
            prop_action = Gio.SimpleAction.new("properties", None)
            prop_action.connect("activate", self._on_channel_properties)
            self._context_action_group.add_action(prop_action)
            search_action = Gio.SimpleAction.new("search", None)
            search_action.connect("activate", self._on_channel_search)
            self._context_action_group.add_action(search_action)
            self.insert_action_group("context", self._context_action_group)
            context_menu_builder = Gtk.Builder.new_from_resource(
                "/org/gnome/gitlab/ranchester/Mirdorph/ui/context_menu.ui"
            )
            context_menu = context_menu_builder.get_object(
                "contextMenu"
            )
            self._context_menu_popover.bind_model(context_menu)


        elif self.empty:
            self._context_menu_button.destroy()
            self._popout_button.destroy()
            self._popin_button.destroy()
            self._popout_button_stack.destroy()
            self._toplevel_empty_stack.set_visible_child(self._empty_status_page)

    # Would be better to move this to main_win instead,
    # this is curently temp as we need to popin, however
    # we could just go through the list of channel contexts.
    def handle_flap_folding(self, flap, folded):
        if flap.get_folded():
            self._flap_toggle_button.set_visible(True)
            self._popout_button_stack.set_visible(False)
            flap.set_swipe_to_close(True)

            self.popin()
        else:
            self._flap_toggle_button.set_visible(False)
            self._popout_button_stack.set_visible(True)
            flap.set_swipe_to_close(False)

    # wrapper to load history in the messageview for message sending
    def load_history(self):
        self._message_view.load_history()

    # Could be better if this was defined in message_view instead?
    @property
    def is_loading_history(self):
        # Not using the spinner like before because .get_active()
        # seems undocumented and broken right now
        return self._loading_history

    def signify_loading_hs(self):
        self._loading_history = True

    def signify_stopped_loading_hs(self):
        self._loading_history = False

    @property
    def history_loading_is_complete(self):
        """
        Wrapper around message view's is history loading complete
        """

        return self._message_view.history_loading_is_complete


    def scroll_messages_to_bottom(self):
        """
        Scroll the view to the very bottom

        NOTE: you need to add to this box BEFORE you scroll
        if you wish to go to the real bottom
        """

        adj = self._message_view.get_vadjustment()
        adj.set_value(adj.get_upper())

    @property
    def is_scroll_at_bottom(self):
        """
        Is the user currently scrolled to the very bottom of the
        view
        """
        adj = self._message_view.get_vadjustment()
        # We can't check for it exactly, because if you scroll
        # for some reason it isn't the true bottom. So we use an "almost"
        # Also, we currently use this when showing the attachment bar

        # NOTE: for when attachment bar reveals, this for some reason doesn't
        # work with taller windows. However if I increase it it doesn't work at all!
        difference = abs(adj.get_value() - adj.get_upper())
        return difference < 600

    def popin(self):
        """
        Popin back to the main window
        """

        try:
            assert self._popout_window
        except AttributeError:
            logging.warning('attempted popin even though not popped out')
            return

        self._popout_button_stack.set_visible_child(self._popout_button)

        self._popout_window.remove(self)
        self._popout_window.destroy()
        # If we don't then the popin detection and folding breaks
        del(self._popout_window)

        self.app.main_win.unconfigure_popout_window(self)
        self.is_poped = False

    # If you are here because of all the random CRITICAL Gtk
    # assertion warnings, I think you're in the wrong place.
    # they started appearing after 1860e9aff877a5493b2c9dbd4db0456ed0d61466
    # even though that changed NOTHING todo with popout
    def popout(self):
        """
        Popout the channel into a separate window
        """

        self.app.main_win.context_stack.remove(self)

        self.app.main_win.reconfigure_for_popout_window()

        self._popout_window = Handy.Window(
            default_width=650,
            default_height=470
        )
        self._popout_window.add(self)
        self._popout_window.present()
        self._popout_button_stack.set_visible_child(self._popin_button)
        self.is_poped = True

    def prepare_scroll_for_msg_send(self):
        """
        Schedule next message to cause screen to scroll
        """
        self._msg_sending_scrl_mode_en = True

    def unprepare_scroll_for_msg_send(self):
        """
        Disable mode of scheduling next messages to cause
        screen to scroll
        """
        self._msg_sending_scrl_mode_en = False

    @property
    def is_scroll_for_msg_send(self):
        """
        Wether currently the next received message is expected to be
        the one sent by the user, and it is expected that the view
        is scrolled to their message
        """
        return self._msg_sending_scrl_mode_en

    @Gtk.Template.Callback()
    def _on_popout_context_button_clicked(self, button):
        self.popout()

    @Gtk.Template.Callback()
    def on_popin_context_button_clicked(self, button):
        self.popin()

    @Gtk.Template.Callback()
    def _on_flap_toggle_button_clicked(self, button):
        self.app.main_win.main_flap.set_reveal_flap(
            not self.app.main_win.main_flap.get_reveal_flap()
        )

    def _on_channel_properties(self, action, param):
        properties_window = ChannelPropertiesWindow(channel=self.channel_disc)
        properties_window.set_modal(True)
        if self.is_poped:
            properties_window.set_transient_for(self._popout_window)
        else:
            properties_window.set_transient_for(self.app.main_win)
        properties_window.present()

    def _on_channel_search(self, action, param):
        # placeholder
        print(f"channel search for {self.channel_disc.name}")

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

class AttachmentType(Enum):
    IMAGE = 0
    GENERIC = 1

# Meant for subclassing
class MirdorphAttachment:
    def __init__(self, attachment):
        self._attachment_disc: discord.Attachment = attachment

    def _do_template_render(self):
        """
        Do the initial rendering before fetching
        discord data
        """
        pass

    def _do_full_render_at(self):
        """
        Start doing the full render, expected to call
        thread that fetches discord, etc
        """
        pass

@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/generic_attachment.ui")
class GenericAttachment(Gtk.ListBox, MirdorphAttachment):
    __gtype_name__ = "GenericAttachment"

    _download_button: Gtk.Button = Gtk.Template.Child()
    _filename_label: Gtk.Label = Gtk.Template.Child()
    _download_progress_bar: Gtk.ProgressBar = Gtk.Template.Child()
    _download_button_image: Gtk.Image = Gtk.Template.Child()

    # Capture attachment to not pass it on to the widget
    def __init__(self, attachment, *args, **kwargs):
        MirdorphAttachment.__init__(self, attachment)
        Gtk.ListBox.__init__(self, *args, **kwargs)

        self._do_template_render()
        self._do_full_render_at()
        self._finished_download = False

    def _do_template_render(self):
        pass

    def _do_full_render_at(self):
        # We don't actually need a separate thread for this
        self._filename_label.set_label(self._attachment_disc.filename)
        self._download_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def _on_listbox_row_activated(self, list_box, row):
        # We only have one row, so this is the main row
        if not self._finished_download:
            self._download_button.clicked()

    @Gtk.Template.Callback()
    def _on_download_button_clicked(self, button):
        logging.info(f"saving attachment {self._attachment_disc.url}")
        self._download_button.set_sensitive(False)
        self._download_progress_bar.pulse()
        save_attachment_thread = threading.Thread(target=self._save_attachment_target)
        save_attachment_thread.start()

    def _pulse_target(self):
        while not self._finished_download:
            time.sleep(0.5)
            GLib.idle_add(lambda _ : self._download_progress_bar.pulse(), None)
        else:
            GLib.idle_add(lambda _ : self._download_progress_bar.set_fraction(1.0), None)

    async def _do_save(self, download_dir):
        save_path = Path(download_dir + "/" + self._attachment_disc.filename)
        await self._attachment_disc.save(str(save_path))

    def _save_attachment_target(self):
        # Magic string editing required because xdg-user-dir output isn't completely clean
        download_dir = str(subprocess.check_output('xdg-user-dir DOWNLOAD', shell=True, text=True))[:-1]

        pulse_thread = threading.Thread(target=self._pulse_target)
        pulse_thread.start()

        asyncio.run_coroutine_threadsafe(
            self._do_save(download_dir),
            Gio.Application.get_default().discord_loop
        ).result()

        self._finished_download = True

        GLib.idle_add(lambda _ : self._download_button_image.set_from_icon_name("emblem-ok-symbolic", 4), None)

class ImageAttachmentLoadingTemplate(Gtk.Bin):
    __gtype_name__ = "ImageAttachmentLoadingTemplate"

    def __init__(self, width: int, height: int, *args, **kwargs):
        Gtk.Bin.__init__(self, width_request=width, height_request=height, *args, **kwargs)

        self.get_style_context().add_class("image-attachment-template")
        self._spinner = Gtk.Spinner(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, 
            width_request=48, height_request=48)
        self._spinner.show()
        self.add(self._spinner)
        self._spinner.start()

class ImageAttachment(MirdorphAttachment, Gtk.Bin):
    __gtype_name__ = "ImageAttachment"

    _image_cache_dir_path = Path(os.environ["XDG_CACHE_HOME"]) / Path("mirdorph")

    # Attachment argument captured to not pass it to widget gtk
    def __init__(self, attachment, *args, **kwargs):
        MirdorphAttachment.__init__(self, attachment)
        Gtk.Bin.__init__(self, *args, **kwargs)

        self._image_stack = Gtk.Stack()
        self._image_stack.show()
        self.add(self._image_stack)

        self._do_template_render()
        self._do_full_render_at()

    def _get_image_path_from_id(self, image_id: int):
        return Path(self._image_cache_dir_path / Path(
            "attachment_image_" + str(image_id) + os.path.splitext(self._attachment_disc.filename)[1]))

    def _calculate_required_size(self) -> tuple:
        """
        Calculate the best size for the image,

        returns: tuple(width, height)
        """
        DESIRED_WIDTH_STANDARD = 290

        if self._attachment_disc.height > DESIRED_WIDTH_STANDARD:
            DESIRED_WIDTH_STANDARD -= 30
        
        size_allocation = (
            DESIRED_WIDTH_STANDARD,
            (DESIRED_WIDTH_STANDARD*self._attachment_disc.height/self._attachment_disc.width)
        )

        return size_allocation

    def _do_template_render(self):
        self._template_image = ImageAttachmentLoadingTemplate(
            self._calculate_required_size()[0],
            self._calculate_required_size()[1]
        )
        self._template_image.show()
        self._image_stack.add(self._template_image)
        self._image_stack.set_visible_child(self._template_image)

    def _do_full_render_at(self):
        fetch_image_thread = threading.Thread(target=self._fetch_image_target)
        fetch_image_thread.start()

    async def _save_image(self):
        await self._attachment_disc.save(str(self._get_image_path_from_id(self._attachment_disc.id)))

    def _fetch_image_target(self):
        asyncio.run_coroutine_threadsafe(
            self._save_image(),
            Gio.Application.get_default().discord_loop
        ).result()

        # So that they don't try to load all at the same time
        time.sleep(random.uniform(1.25, 3.5)),

        GLib.idle_add(self._load_image_gtk_target)

    def _load_image_gtk_target(self):
        if self._get_image_path_from_id(self._attachment_disc.id).is_file():
            real_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(self._get_image_path_from_id(self._attachment_disc.id)),
                self._calculate_required_size()[0],
                self._calculate_required_size()[1],
                preserve_aspect_ratio=True
            )
            self._real_image = Gtk.Image.new_from_pixbuf(real_pixbuf)
            self._real_image.show()
            self._image_stack.add(self._real_image)
            self._image_stack.set_visible_child(self._real_image)

def get_attachment_type(attachment: discord.Attachment) -> str:
    """
    Get the attachment type of the att

    available_types = AttachmentType.IMAGE
    """

    data_format = os.path.splitext(attachment.filename)
    if data_format[1][1:].lower() in ['jpg', 'jpeg', 'bmp', 'png', 'webp']:
        return AttachmentType.IMAGE
    else:
        return AttachmentType.GENERIC

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
        GLib.idle_add(self._label_color_gtk_target, color_formatted)

    def _label_color_gtk_target(self, color: str):
        self._username_label.set_markup(
            f"<span foreground='{color}'>{self._username_label.get_label()}</span>"
        )

@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message_view.ui')
class MessageView(Gtk.ScrolledWindow, EventReceiver):
    __gtype_name__ = "MessageView"

    _STANDARD_HISTORY_LOADING = 40

    _message_column: Gtk.Box = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.ScrolledWindow.__init__(self, *args, **kwargs)
        EventReceiver.__init__(self)

        self._message_listbox = Gtk.ListBox(hexpand=True, selection_mode=Gtk.SelectionMode.NONE)
        # When nearly empty channel, messages should not pile up on top
        self._message_listbox.set_valign(Gtk.Align.END)
        self._message_listbox.get_style_context().add_class("message-history")

        # Due to events, the messages might often become out of order
        # this ensures that the messages that were created earlier
        # are always displayed *before* the later ones. This is for history
        def message_listbox_sort_func(row_1, row_2, data, notify_destroy):
            # For history loading spinner, which is a special case
            if not isinstance(row_1, MirdorphMessage) or not isinstance(row_2, MirdorphMessage):
                return -1
            if row_1.timestamp < row_2.timestamp:
                return -1
            else:
                return (row_1.timestamp < row_2.timestamp) + 1

        self._message_listbox.set_sort_func(message_listbox_sort_func, None, False)
        self._message_listbox.show()

        self._history_loading_row = Gtk.ListBoxRow(height_request=32)
        self._history_loading_row.show()
        self._history_loading_spinner = Gtk.Spinner()
        self._history_loading_spinner.show()
        self._history_loading_row.add(self._history_loading_spinner)
        self._message_listbox.add(self._history_loading_row)

        self._message_clamp = Handy.Clamp(maximum_size=800, tightening_threshold=600)
        self._message_clamp.show()
        self._message_clamp.add(self._message_listbox)
        self._message_column.add(self._message_clamp)

        self._adj = self.get_vadjustment()
        self._orig_upper = self._adj.get_upper()
        self._balance = None
        self._autoscroll = False

        self.context = context

    def set_balance_top(self):
        # DONTFIXME: Workaround: https://gitlab.gnome.org/GNOME/gtk/merge_requests/395
        self.set_kinetic_scrolling(False)
        self._balance = Gtk.PositionType.TOP

    def _handle_upper_adj_notify(self, upper, adjparam):
        new_upper = self._adj.get_upper()
        diff = new_upper - self._orig_upper

        # Don't do anything if upper didn't change
        if diff != 0.0:
            self._orig_upper = new_upper
            if self._autoscroll:
                self._adj.set_value(self._adj.get_upper() - self._adj.get_page_size())
            elif self._balance == Gtk.PositionType.TOP:
                self._balance = False
                self._adj.set_value(self._adj.get_value() + diff)
                self.set_kinetic_scrolling(True)

    def _handle_value_adj_changed(self, adj):
        bottom = adj.get_upper() - adj.get_page_size()
        self._autoscroll = (abs(adj.get_value() - bottom) < sys.float_info.epsilon)
        if adj.get_value() < adj.get_page_size() * 1.5:
            self.load_history(additional=15)

    def build_scroll(self):
        self._adj.connect("notify::upper", self._handle_upper_adj_notify)
        self._adj.connect("value-changed", self._handle_value_adj_changed)


    def _on_msg_send_mode_scl_send_wrap(self):
        self.context.scroll_messages_to_bottom()

    def disc_on_message(self, message):
        if message.channel.id == self.context.channel_id:
            message_wid = MirdorphMessage(message)
            message_wid.show()
            # No risk of this being a duplicate as this event never happens twice
            self._message_listbox.add(message_wid)

            if self.context.is_scroll_for_msg_send or self.context.is_scroll_at_bottom:
                # With GLIB.idle_add and a wrapper instead of directly,
                # since for some reason it only works like this.
                GLib.idle_add(self._on_msg_send_mode_scl_send_wrap)

            # We unset it here since currently it always intended for one message - the next one
            # And it is extremely unlikely that the next on_message isn't the one that has been sent.
            # This isnt called in the async send msg function with GLib.idle_add because it for some
            # reason executes in the wrong order then and misses the message
            # However this now be a bit different (seems a bit more accurate) with the additional
            # Fractal scrolling code.
            self.context.unprepare_scroll_for_msg_send()

    @property
    def history_loading_is_complete(self):
        """
        If history loading has completed atleast once

        This is useful for calling something that depends on history getting loaded,
        like scrolling the messages to the bottom for the first time. Not 100% accurate
        """
        # Works as the message listboxes are direct children of the message listbox
        # However not 100% accurate as some could have been from on_message,
        # but that is highly unlikely
        for child in self._message_listbox.get_children():
            if isinstance(child, MirdorphMessage):
                return True
        return False

    async def _get_history_messages_to_list(self, channel, amount_to_load):
        """
        Return a list of Discord messages in current history,
        useful to call in other thread and use the list to build
        message objects
        """
        tmp_list = []
        async for message in channel.history(limit=amount_to_load):
            tmp_list.append(message)
        return tmp_list

    def _history_loading_gtk_target(self, messages: list):
        for message in messages:
            # We need to check for duplicates and not add it if it is one
            # because load_history will often be called multiple times
            duplicate = False
            # The message listbox currently just has messages directly as children
            # so this work fine
            for already_existing_message in self._message_listbox.get_children():
                if (isinstance(already_existing_message, MirdorphMessage) and
                    message.id == already_existing_message.uniq_id):
                        duplicate = True
                        break
            if not duplicate:
                message_wid = MirdorphMessage(message)
                message_wid.show()
                self.set_balance_top()
                self._message_listbox.add(message_wid)

        self._history_loading_spinner.stop()
        self.context.signify_stopped_loading_hs()

    def _history_loading_target(self, additional):
        amount_to_load = self._STANDARD_HISTORY_LOADING
        if additional is not None:
            amount_to_load = len(self._message_listbox.get_children()) + additional

        messages = list(
            asyncio.run_coroutine_threadsafe(
                self._get_history_messages_to_list(
                    self.context.channel_disc,
                    amount_to_load
                ),
                Gio.Application.get_default().discord_loop
            ).result()
        )

        GLib.idle_add(self._history_loading_gtk_target, messages)

    def load_history(self, additional=None):
        """
        Load the history of the view and it's channel

        You can only load once at a time, async operation

        param:
            additional - additional ammount of messages to load, useful
            only if previously loaded
        """
        if self.context.is_loading_history:
            logging.warning("attempted to load history even if already loading")
            return
        self.context.signify_loading_hs()
        self._history_loading_spinner.start()
        message_loading_thread = threading.Thread(target=self._history_loading_target, args=(additional,))
        message_loading_thread.start()


@Gtk.Template(resource_path='/org/gnome/gitlab/ranchester/Mirdorph/ui/message_entry_bar_attachment.ui')
# Should be Gtk.bin but then padding and margin don't work?
class MessageEntryBarAttachment(Gtk.Button):
    __gtype_name__ = "MessageEntryBarAttachment"

    _mode_stack: Gtk.Stack = Gtk.Template.Child()
    _mode_content_box: Gtk.Box = Gtk.Template.Child()
    _mode_add_image: Gtk.Image = Gtk.Template.Child()
    _filename_label: Gtk.Label = Gtk.Template.Child()

    # Ugly passing this when adding this because we need to be able to signify when
    # we added a new attachment to update send button
    # Gtk Box doesn't emit add signal
    def __init__(self, parent_for_sign=None, add_mode=True, filename=None, *args, **kwargs):
        Gtk.Button.__init__(self, *args, **kwargs)
        self.add_mode = add_mode
        self.full_filename = filename
        self._parent_for_sign = parent_for_sign
        if self.full_filename:
            self.add_mode = False
            self.set_sensitive(False)
            self._mode_stack.set_visible_child(self._mode_content_box)
            load_details_thread = threading.Thread(target=self._load_details_target)
            load_details_thread.start()

    def _load_details_target(self):
        # Not really useful to have separate thread with only name
        file_object_call = Path(self.full_filename).name
        GLib.idle_add(self._load_details_gtk_target, file_object_call)

    def _load_details_gtk_target(self, file_object_call: str):
        self._filename_label.set_label(file_object_call)

    @Gtk.Template.Callback()
    def _on_add_clicked(self, button):
        if self.add_mode:
            native_dialog = Gtk.FileChooserNative.new(
                "Select File to Upload",
                Gio.Application.get_default().main_win,
                Gtk.FileChooserAction.OPEN,
                None,
                None
            )
            response = native_dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                self.get_parent().pack_start(
                    MessageEntryBarAttachment(visible=True, add_mode=False, filename=native_dialog.get_filename()),
                    False,
                    False,
                    0
                )
                # Ugly hack since gtk box doesn't emit add
                assert self._parent_for_sign is not None
                self._parent_for_sign.emulate_attachment_container_change()

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
            self.context.channel_disc.send(message, files=atts_to_send),
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
    def _on_revealer_child_revealed(self, revealer, param):
        # Looks a bit weird, maybe better to listen to when the position of the message view changes
        # and constanly update scroll to bottom? TODO
        if self._attachment_area_revealer.get_child_revealed() and self.context.is_scroll_at_bottom:
            self.context.scroll_messages_to_bottom()

    # Gtk Box does not support this, so we will do it manually when we add
    def emulate_attachment_container_change(self):
        if len(self._attachment_container.get_children()) > 1:
            self._send_button.set_sensitive(True)
            self._send_button.get_style_context().add_class("suggested-action")
