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
from gettext import gettext as _
from enum import Enum
from pathlib import Path
from gi.repository import Gtk, Gio, GObject, GLib, GdkPixbuf


class AttachmentType(Enum):
    IMAGE = 0
    GENERIC = 1


# Meant for subclassing
class MirdorphAttachment:
    def __init__(self, attachment: discord.Attachment, channel_id: int):
        self._attachment_disc: discord.Attachment = attachment
        self._channel_id = channel_id

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

    def __init__(self, attachment, channel_id: int, *args, **kwargs):
        MirdorphAttachment.__init__(self, attachment, channel_id)
        Gtk.ListBox.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self._finished_download = False

        self._do_template_render()
        self._do_full_render_at()

    def _do_template_render(self):
        pass

    def _do_full_render_at(self):
        self._filename_label.set_label(self._attachment_disc.filename)
        self._download_button.set_sensitive(True)

    @Gtk.Template.Callback()
    def _on_listbox_row_activated(self, list_box, row):
        if not self._finished_download:
            self._download_button.clicked()

    @Gtk.Template.Callback()
    def _on_download_button_clicked(self, button):
        logging.info(f"saving attachment {self._attachment_disc.url}")
        self._download_button.set_sensitive(False)
        GLib.timeout_add(250, self._pulse_target)
        threading.Thread(target=self._save_attachment_target).start()

    def _pulse_target(self):
        if not self._finished_download:
            self._download_progress_bar.pulse()
        else:
            self._download_progress_bar.set_fraction(1.0)
            return False

    async def _do_save(self, download_dir):
        save_path = Path(download_dir + "/" + self._attachment_disc.filename)
        await self._attachment_disc.save(str(save_path))

    def _save_attachment_target(self):
        # Output adds trailing new line
        download_dir = subprocess.check_output("xdg-user-dir DOWNLOAD", shell=True, text=True).rstrip()

        asyncio.run_coroutine_threadsafe(
            self._do_save(download_dir),
            self.app.discord_loop
        ).result()

        self._finished_download = True
        GLib.idle_add(lambda *_ : self._download_button_image.set_from_icon_name("emblem-ok-symbolic", 4))

class ImageAttachmentLoadingTemplate(Gtk.Bin):
    """
    Template of a still "loading" image, it is designed
    in this way because the template and the final result
    MUST be of the exact same size for scrolling to be smooth.
    Luckily Discord automatically gives us image width/height info.
    """
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

    __gsignals__ = {
        "image_fully_loaded": (GObject.SIGNAL_RUN_FIRST, None,
                                 ())
    }

    _image_cache_dir_path = Path(os.environ["XDG_CACHE_HOME"]) / Path("mirdorph")

    # Attachment and channel_id arguments captured to not pass it to widget gtk
    def __init__(self, attachment, channel_id: int, *args, **kwargs):
        MirdorphAttachment.__init__(self, attachment, channel_id)
        Gtk.Bin.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self.image_save_path = self.get_image_save_path(
            self._attachment_disc.id,
            self._attachment_disc.filename
        )

        self._image_stack = Gtk.Stack()
        self._image_stack.show()
        self.add(self._image_stack)

        # Not GtkGestureSingle because it simply doesn't work on its own.
        self.connect("button-press-event", self._on_clicked)

        self._do_template_render()
        self._do_full_render_at()

    # Useful function for image viewer, image_save_path not sufficient because
    # requires instance.
    @staticmethod
    def get_image_save_path(image_id: int, attachment_filename: str):
        return (ImageAttachment._image_cache_dir_path
            / Path(
                "attachment_image_"
                + str(image_id)
                + os.path.splitext(attachment_filename)[1]
            )
        )

    def _on_clicked(self, guesture: Gtk.GestureSingle, sequence):
        context = self.app.retrieve_inner_window_context(
            self._channel_id
        )
        context.show_image_viewer(self._attachment_disc)

    def _calculate_required_size(self) -> tuple:
        """
        Calculate the best size for the image.

        NOTE: this is a temporary solution unil a resizable image
        is implemented, however AtkPicture last time I tried was
        very buggy in this configuration.

        returns: tuple(width, height)
        """
        DESIRED_WIDTH_STANDARD = 290

        try:
            # Very high attachments should be less wide to look more natural.
            if self._attachment_disc.height > DESIRED_WIDTH_STANDARD:
                DESIRED_WIDTH_STANDARD -= 30
        except TypeError:
            # With some very specific attachments this is NoneType.
            # I think in these cases it is best to just return the mishapen
            # image instead
            logging.warning(f"could not get dimentions of {self._attachment_disc}")
            return (DESIRED_WIDTH_STANDARD, DESIRED_WIDTH_STANDARD)

        return (
            DESIRED_WIDTH_STANDARD,
            (DESIRED_WIDTH_STANDARD*self._attachment_disc.height/self._attachment_disc.width)
        )

    def _do_template_render(self):
        self._template_image = ImageAttachmentLoadingTemplate(
            self._calculate_required_size()[0],
            self._calculate_required_size()[1]
        )
        self._template_image.show()
        self._image_stack.add(self._template_image)

    def _do_full_render_at(self):
        threading.Thread(target=self._fetch_image_target).start()

    def _fetch_image_target(self):
        asyncio.run_coroutine_threadsafe(
            self._attachment_disc.save(str(self.image_save_path)),
            self.app.discord_loop
        ).result()

        GLib.idle_add(self._load_image_gtk_target)

    def _load_image_gtk_target(self):
        if self.image_save_path.is_file():
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(self.image_save_path),
                self._calculate_required_size()[0],
                self._calculate_required_size()[1],
                preserve_aspect_ratio=True
            )
            self._real_image = Gtk.Image.new_from_pixbuf(pixbuf)
            self._real_image.show()

            # This seems really weird, but for ::button-press-event to work
            # we need to create a gesture for this widget. It is completely
            # unrelated.
            # However this is still quite useful as we can no that on_click
            # only happens after the image has been downloaded.
            self._gesture = Gtk.GestureSingle(widget=self._real_image)

            self._image_stack.add(self._real_image)
            self._image_stack.set_visible_child(self._real_image)

            self.emit("image_fully_loaded")

def get_attachment_type(attachment: discord.Attachment) -> str:
    """
    Get the attachment type of the att

    available_types = AttachmentType.IMAGE, AttachmentType.GENERIC
    """
    data_format = os.path.splitext(attachment.filename)
    if data_format[1][1:].lower() in ["jpg", "jpeg", "bmp", "png", "webp"]:
        return AttachmentType.IMAGE
    else:
        return AttachmentType.GENERIC


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/message_entry_bar_attachment.ui")
class MessageEntryBarAttachment(Gtk.Button):
    __gtype_name__ = "MessageEntryBarAttachment"

    _mode_stack: Gtk.Stack = Gtk.Template.Child()
    _mode_content_box: Gtk.Box = Gtk.Template.Child()
    _filename_label: Gtk.Label = Gtk.Template.Child()

    # Passing the attachment bar here as parent_for_sign as GtkBox doesn't work correctly
    # with the ::add signal.
    def __init__(self, parent_for_sign=None, add_mode=True, filename=None, *args, **kwargs):
        Gtk.Button.__init__(self, *args, **kwargs)
        self.add_mode = add_mode
        self.full_filename = filename
        self._parent_for_sign = parent_for_sign
        if self.full_filename:
            self.add_mode = False
            self.set_sensitive(False)
            self._mode_stack.set_visible_child(self._mode_content_box)
            threading.Thread(target=self._load_details_target).start()

    def _load_details_target(self):
        # Not really useful to have separate thread with only name,
        # However with images this would be very useful
        file_object_call = Path(self.full_filename).name
        GLib.idle_add(self._load_details_gtk_target, file_object_call)

    def _load_details_gtk_target(self, file_object_call: str):
        self._filename_label.set_label(file_object_call)

    @Gtk.Template.Callback()
    def _on_add_clicked(self, button):
        if self.add_mode:
            window = self.get_toplevel()
            filechooser = Gtk.FileChooserNative.new(
                _("Select File to Upload"),
                window if window.is_toplevel() else None,
                Gtk.FileChooserAction.OPEN,
                None,
                None
            )
            response = filechooser.run()
            if response == Gtk.ResponseType.ACCEPT:
                self.get_parent().pack_start(
                    MessageEntryBarAttachment(visible=True, add_mode=False, filename=filechooser.get_filename()),
                    False,
                    False,
                    0
                )
                self._parent_for_sign.emulate_attachment_container_change()
