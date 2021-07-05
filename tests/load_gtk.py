# Loading the Gresource for importing modules with composite templates, and stuff like
# Adw.init + version requires
import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio
# About dialog is created by meson which we can't use
os.system("sed '/about_dialog/d' ../data/mirdorph.gresource.xml > ../data/unmeson-mirdorph.gresource.xml")
os.system("cd ../data/ && glib-compile-resources unmeson-mirdorph.gresource.xml")
resource = Gio.resource_load("../data/unmeson-mirdorph.gresource")
Gio.Resource._register(resource)

from gi.repository import Adw
Adw.init()
