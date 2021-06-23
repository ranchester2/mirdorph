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
from pathlib import Path
from gi.repository import Gtk, Gdk, GLib, Gio, Handy
from .atkpicture import AtkPicture


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/image_viewer.ui")
class ImageViewer(Handy.Flap):
    __gtype_name__ = "ImageViewer"

    _picture_container: Gtk.ScrolledWindow = Gtk.Template.Child()
    _headerbar: Handy.HeaderBar = Gtk.Template.Child()
    _fullscreen_button_image: Gtk.Image = Gtk.Template.Child()

    _mouse_hover_eventbox: Gtk.EventBox = Gtk.Template.Child()
    _catalog_buttons_revealer: Gtk.Revealer = Gtk.Template.Child()

    def __init__(self, context, *args, **kwargs):
        Handy.Flap.__init__(self, *args, **kwargs)
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

        # Doesn't work by default
        self._mouse_hover_eventbox.set_events(Gdk.EventMask.POINTER_MOTION_MASK)
        # When switching channels, this will "pile up"
        # FIXME: it is counted as an umap when a window is being popped in
        self.connect("unmap", self._remove_existing_image)

    @Gtk.Template.Callback()
    def _on_back_button_clicked(self, button: Gtk.Button):
        self.context.exit_image_viewer()

    @Gtk.Template.Callback()
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

                self.set_fold_policy(Handy.FlapFoldPolicy.NEVER)
                self.set_reveal_flap(True)

                self._is_fullscreen = False
            else:
                window.fullscreen()
                self._fullscreen_button_image.set_from_icon_name(
                    "view-restore-symbolic",
                    Gtk.IconSize.BUTTON
                )

                self.set_fold_policy(Handy.FlapFoldPolicy.ALWAYS)
                self.set_reveal_flap(True)

                self._is_fullscreen = True

    def _remove_existing_image(self, *args):
        if self._picture_container.get_children():
            self._picture_container.get_children()[0].destroy()
            self._current_image_path = None

    def display_image(self, attachment: discord.Attachment):
        self._remove_existing_image()
        # It is safe to assume that the picture exists, because the click to open the ImagePreview
        # can only happen after the image is downloaded
        self._current_image_path = Path(
            Path(os.environ["XDG_CACHE_HOME"]) / Path("mirdorph") / Path(
            "attachment_image_" + str(attachment.id) + os.path.splitext(attachment.filename)[1])
        )
        picture_wid = AtkPicture(
            str(self._current_image_path),
            self._picture_container,
            max_width=attachment.width if attachment.width else 0,
            vexpand=True,
            hexpand=True,
            valign=Gtk.Align.CENTER
        )
        picture_wid.show()
        self._picture_container.add(picture_wid)

        self._headerbar.set_title(attachment.filename)
