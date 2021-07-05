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
import time
import os
import subprocess
import asyncio
import threading
from pathlib import Path
from gi.repository import Gtk, Gdk, GLib, Gio, Adw
from .atkpicture import AtkPicture
from .attachment import ImageAttachment, AttachmentType, get_attachment_type


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/image_viewer.ui")
class ImageViewer(Adw.Flap):
    __gtype_name__ = "ImageViewer"

    _picture_container: Gtk.ScrolledWindow = Gtk.Template.Child()
    _headerbar: Adw.HeaderBar = Gtk.Template.Child()
    _fullscreen_button_image: Gtk.Image = Gtk.Template.Child()

    _mouse_hover_eventbox: Gtk.EventBox = Gtk.Template.Child()
    _catalog_buttons_revealer: Gtk.Revealer = Gtk.Template.Child()
    _catalog_forward: Gtk.Button = Gtk.Template.Child()
    _catalog_back: Gtk.Button = Gtk.Template.Child()
    _loading_notif_revealer: Gtk.Revealer = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Adw.Flap.__init__(self, *args, **kwargs)
        self.context = context
        self.app = Gio.Application.get_default()

        self._last_show_catalog_button_time = None
        self._current_image_path: Path = None
        # It is recommended to not assume from .fullscreen()
        # However, using ::window-state-event causes MASSIVE
        # performance problems
        self._is_fullscreen = False

        self._image_viewer_action_group = Gio.SimpleActionGroup()

        open_in_app = Gio.SimpleAction.new("open-in-app", None)
        open_in_app.connect("activate", self._action_open_in_app)
        self._image_viewer_action_group.add_action(open_in_app)
        fullscreen = Gio.SimpleAction.new("fullscreen", None)
        fullscreen.connect("activate", self._action_fullscreen)
        self._image_viewer_action_group.add_action(fullscreen)

        self.insert_action_group("image-viewer", self._image_viewer_action_group)

        self._mouse_hover_eventbox.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self._motion_event_controller = Gtk.EventControllerMotion(widget=self._mouse_hover_eventbox)
        self._motion_event_controller.connect("motion", self._on_motion)

    @Gtk.Template.Callback()
    def _on_back_button_clicked(self, button: Gtk.Button):
        self.context.exit_image_viewer()

    def _on_motion(self, *args):
        def waiting_callback():
            if (self._last_show_catalog_button_time) + 3 >= time.time():
                return True
            else:
                self._catalog_buttons_revealer.set_reveal_child(False)
                return False

        self._catalog_buttons_revealer.set_reveal_child(True)
        self._last_show_catalog_button_time = time.time()
        GLib.timeout_add(
            250,
            waiting_callback
        )

    @Gtk.Template.Callback()
    def _on_navigate_forward(self, button: Gtk.Button):
        threading.Thread(
            target=self._navigate_media_target,
            args=(True,)
        ).start()

    @Gtk.Template.Callback()
    def _on_navigate_back(self, button: Gtk.Button):
        threading.Thread(
            target=self._navigate_media_target,
            args=(False,)
        ).start()

    async def _check_if_first_media(self) -> bool:
        async for message in self.context.channel_disc.history(limit=None):
            for attachment in message.attachments:
                if self._current_attachment == attachment:
                    return True

                if get_attachment_type(attachment) == AttachmentType.IMAGE:
                    return False
        # Very rare edge case (deleted) if this is executed
        return True

    def _check_if_first_media_target(self):
        is_first = asyncio.run_coroutine_threadsafe(
            self._check_if_first_media(),
            self.app.discord_loop
        ).result()
        GLib.idle_add(lambda *_: self._catalog_back.set_visible(not is_first))

    def _signify_catalog_load_start(self):
        self._loading_notif_revealer.set_reveal_child(True)
        self._catalog_forward.set_sensitive(False)
        self._catalog_back.set_sensitive(False)

    def _signify_catalog_load_end(self):
        self._loading_notif_revealer.set_reveal_child(False)
        self._catalog_forward.set_sensitive(True)
        self._catalog_back.set_sensitive(True)

    async def _get_next_attachment(self) -> discord.Attachment:
        async for message in self.context.channel_disc.history(limit=None, before=self._current_attachment):
            for attachment in message.attachments:
                if get_attachment_type(attachment) == AttachmentType.IMAGE:
                    return attachment
                else:
                    continue
        # There are no further attachments
        return None

    async def _get_previous_attachment(self) -> discord.Attachment:
        # Even though we use after, the current message seems to still be included often
        # but not always, which is why if we encounter our attachment we skip it.
        async for message in self.context.channel_disc.history(limit=None, after=self._current_attachment):
            for attachment in message.attachments:
                if get_attachment_type(attachment) == AttachmentType.IMAGE:
                    if attachment != self._current_attachment:
                        return attachment
                else:
                    continue
        # Was triggered before disabling the back navigation button,
        # if this is the first one.
        return None

    def _setup_new_imge(self, new_attachment: discord.Attachment):
        new_image_wid = ImageAttachment(
            new_attachment, self.context.channel_id)

        def on_full_render(image_attachment: ImageAttachment):
            self.display_image(new_attachment)
            self._signify_catalog_load_end()

        new_image_wid.connect("image_fully_loaded", on_full_render)

    def _navigate_media_target(self, forward: bool):
        GLib.idle_add(self._signify_catalog_load_start)

        if forward:
            next_attachment = asyncio.run_coroutine_threadsafe(
                self._get_next_attachment(),
                self.app.discord_loop
            ).result()
            if next_attachment:
                GLib.idle_add(self._setup_new_imge, next_attachment)
            else:
                self._signify_catalog_load_end()
        else:
            previous_attachment = asyncio.run_coroutine_threadsafe(
                self._get_previous_attachment(),
                self.app.discord_loop
            ).result()
            if previous_attachment:
                GLib.idle_add(self._setup_new_imge, previous_attachment)
            else:
                self._signify_catalog_load_end()

    def _action_open_in_app(self, *args):
        subprocess.run(["xdg-open", str(self._current_image_path)])

    def _action_fullscreen(self, *args):
        window = self.get_toplevel()
        if window.is_toplevel():
            if self._is_fullscreen:
                window.unfullscreen()
                self._fullscreen_button_image.set_from_icon_name(
                    "view-fullscreen-symbolic",
                    Gtk.IconSize.BUTTON
                )

                self._headerbar.set_show_close_button(True)
                self.set_fold_policy(Adw.FlapFoldPolicy.NEVER)
                self.set_reveal_flap(True)

                self._is_fullscreen = False
            else:
                window.fullscreen()
                self._fullscreen_button_image.set_from_icon_name(
                    "view-restore-symbolic",
                    Gtk.IconSize.BUTTON
                )

                self._headerbar.set_show_close_button(False)
                self.set_fold_policy(Adw.FlapFoldPolicy.ALWAYS)
                self.set_reveal_flap(True)

                self._is_fullscreen = True

    def _remove_existing_image(self, *args):
        if self._picture_container.get_children():
            self._picture_container.remove(
                self._picture_container.get_children()[0]
            )
            self._current_image_path = None

    def display_image(self, attachment: discord.Attachment):
        self._remove_existing_image()

        self._current_attachment = attachment
        # It is safe to assume that the picture exists, because the click to open the ImagePreview
        # can only happen after the image is downloaded
        self._current_image_path = ImageAttachment.get_image_save_path(
            self._current_attachment.id,
            self._current_attachment.filename
        )
        picture_wid = AtkPicture(
            str(self._current_image_path),
            self._picture_container,
            max_width=self._current_attachment.width if self._current_attachment.width else 0,
            vexpand=True,
            hexpand=True,
            valign=Gtk.Align.CENTER
        )
        picture_wid.show()
        self._picture_container.add(picture_wid)

        self._headerbar.set_title(self._current_attachment.filename)

        threading.Thread(target=self._check_if_first_media_target).start()
