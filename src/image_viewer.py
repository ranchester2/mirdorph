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

from gi.repository import Gtk, Gio


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/image_viewer.ui")
class ImageViewer(Gtk.Box):
    __gtype_name__ = "ImageViewer"

    def __init__(self, context, *args, **kwargs):
        Gtk.Box.__init__(self, *args, **kwargs)
        self.context = context
        self.app = Gio.Application.get_default()

    @Gtk.Template.Callback()
    def _on_back_button_clicked(self, button: Gtk.Button):
        self.context.exit_image_viewer()
