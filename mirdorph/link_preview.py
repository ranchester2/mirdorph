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

import linkpreview
import threading
import logging
import requests
import urllib
import hashlib
import os
import gi
from pathlib import Path
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/link_preview.ui")
class LinkPreviewExport(Gtk.ListBox):
    __gtype_name__ = "LinkPreviewExport"

    _image_dir_path = Path(os.environ["XDG_CACHE_HOME"] / Path("mirdorph"))

    _link_label: Gtk.Label = Gtk.Template.Child()
    _link_image: Gtk.Image = Gtk.Template.Child()

    def __init__(self, link: str, *args, **kwargs):
        Gtk.ListBox.__init__(self, *args, **kwargs)
        self.link = link
        self._link_label.set_label(link)

        threading.Thread(target=self._fetch_preview).start()

    def _fetch_preview(self):
        try:
            preview = linkpreview.link_preview(self.link)
        except:
            logging.warning(f"could not get preview for {self.link}")
            return

        image_path = None
        if preview.image:
            try:
                r = requests.get(preview.image)
            except requests.exceptions.MissingSchema:
                # Some websites use relative links, which is why this is needed
                parsed = urllib.parse.urlparse(self.link)
                url_with_schema = parsed.scheme + "://" + parsed.netloc + preview.image
                r = requests.get(url_with_schema)

            web_image_path = urllib.parse.urlparse(preview.image).path
            ext = os.path.split(web_image_path)[1]
            file_hash = hashlib.sha256(preview.image.encode("utf-8")).hexdigest()

            image_path = self._image_dir_path / \
                Path(f"link_image_{file_hash}.{ext}")

            with open(image_path, "wb") as f:
                f.write(r.content)

        GLib.idle_add(self._display_preview, preview.title, image_path)

    def _display_preview(self, title: str, image_path: str):
        if title:
            self._link_label.set_label(title)
        if image_path:
            try:
                image_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(image_path),
                    # 120 = request(140) - some phantom 20 - the padding (optional??)
                    120,
                    120,
                    False
                )
            except gi.repository.GLib.Error:
                logging.warning(f"attempted to load load GIF preview for {self.link}")
                return
            self._link_image.set_from_pixbuf(image_pixbuf)

    @Gtk.Template.Callback()
    def _on_row_activated(self, listbox, row):
        Gtk.show_uri_on_window(None, self.link, Gdk.CURRENT_TIME)
