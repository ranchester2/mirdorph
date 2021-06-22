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
import os
from pathlib import Path
from gi.repository import Gtk, Gio
from .atkpicture import AtkPicture


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/image_viewer.ui")
class ImageViewer(Gtk.Box):
    __gtype_name__ = "ImageViewer"

    _picture_container: Gtk.Box = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        self.context = context
        self.app = Gio.Application.get_default()

        # When switching channels, this will "pile up"
        self.connect("unmap", self._remove_existing_image)

    @Gtk.Template.Callback()
    def _on_back_button_clicked(self, button: Gtk.Button):
        self.context.exit_image_viewer()

    def _remove_existing_image(self, *args):
        if self._picture_container.get_children():
            self._picture_container.get_children()[0].destroy()

    def display_image(self, attachment: discord.Attachment):
        self._remove_existing_image()
        # It is safe to assume that the picture exists, because the click to open the ImagePreview
        # can only happen after the image is downloaded
        image_path = Path(
            Path(os.environ["XDG_CACHE_HOME"]) / Path("mirdorph") / Path(
            "attachment_image_" + str(attachment.id) + os.path.splitext(attachment.filename)[1])
        )
        picture_wid = AtkPicture(
            str(image_path),
            max_width=attachment.width if attachment.width else 0,
            vexpand=True,
            hexpand=True,
            valign=Gtk.Align.CENTER
        )
        picture_wid.show()
        self._picture_container.add(picture_wid)
