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
import subprocess
import discord
import os
import time
import random
from enum import Enum
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Gdk, GdkPixbuf, Handy


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
