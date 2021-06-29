# Loading the Gresource for importing modules with composite templates
import os
import gi
from gi.repository import Gio
# About dialog is created by meson which we can't use
os.system("sed '/about_dialog/d' ../data/mirdorph.gresource.xml > ../data/unmeson-mirdorph.gresource.xml")
os.system("cd ../data/ && glib-compile-resources unmeson-mirdorph.gresource.xml")
resource = Gio.resource_load("../data/unmeson-mirdorph.gresource")
Gio.Resource._register(resource)
