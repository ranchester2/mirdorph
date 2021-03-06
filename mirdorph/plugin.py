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

from __future__ import annotations
import os
import sys
import inspect
import json
import logging
import gi
from gi.repository import Gtk, Gio, GObject
from pathlib import Path


class MrdPluginEngine:
    """
    The MrdPluginEngine manages plugins and there should be only one.

    Extension points are implemented via Extension Sets with an api similar
    to libpeas. Your implementation is responsible for loading the plugins.

    You should consult the local documentation for more information.
    """
    # moduledir/plugins
    plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")

    def __init__(self):
        self._extension_points = []
        self._plugins = {}
        self.scan_plugins()

    @staticmethod
    def is_plugin_compatible(plugin: MrdPluginInfo, extension_set: MrdExtensionSet) -> bool:
        """
        Check if a plugin is compatible with an extension set, can be useful when creating
        lists of compatible plugins.

        param:
            plugin: the MrdPluginInfo you want to check
            extension_set: the extension_set to check if compatible with. It is compatible
            if the type of the plugin is a subclass of the type of the extension_set
        """
        try:
            return issubclass(plugin.type, extension_set.type)
        # Base plugins don't have subclasses?
        except TypeError:
            return False

    def scan_plugins(self):
        """
        (Re)Scan the plugin directory for plugins.
        NOTE: Make sure references using old plugins are destroyed before
        rescanning the plugin directory, this should only be optionally used
        for initial setup (note that MrdPluginEngine does this automatically)
        """
        self._plugins.clear()
        for pdir in os.listdir(self.plugins_dir):
            # Pycache, __init__, and other
            if pdir.startswith("__"):
                continue

            plugin_init = {}
            try:
                for file in os.listdir(os.path.join(self.plugins_dir, pdir)):
                    if file.endswith(".plugin"):
                        with open(os.path.join(self.plugins_dir, pdir, file), "r") as f:
                            plugin_init = json.load(f)
            except NotADirectoryError:
                continue
            if plugin_init:
                plugin = MrdPluginInfo(plugin_init, self)
                self._plugins[plugin.module_name] = plugin

    def add_extension_point(self, extension_set: MrdExtensionSet):
        """
        Add an extension set to this engine.
        NOTE: You should not call this! On creation of the extension_set
        it is done automatically!

        param:
            extension_set: the extension set that should be added
        """
        self._extension_points.append(extension_set)

    def get_available_plugins(self) -> list:
        """
        Get a list of all available plugins.

        returns:
            list of `MrdPluginInfo`
        """
        return list(self._plugins.values())

    def get_enabled_plugins(self) -> list:
        """
        Helper function to get only plugins that are enabled.

        returns:
            list of `MrdPluginInfo`
        """
        return [plugin for plugin in list(self._plugins.values()) if plugin.active]

    def get_plugin_from_module(self, module_name: str) -> MrdPluginInfo:
        """
        Get a `MrdPluginInfo` by the name of its module.

        param:
            module_name: `str` the module name of the plugin you want
        returns:
            a `MrdPluginInfo`
        """
        return self._plugins[module_name]

    def _handle_extension_set_plug_signal(self, mode: str, plugin: MrdPluginInfo):
        if mode not in ["add", "remove"]:
            raise Exception(f"mode {mode} is not supported")

        for extension_point in self._extension_points:
            if self.is_plugin_compatible(plugin, extension_point):
                if mode == "add":
                    extension_point.emit("extension_added", plugin)
                elif mode == "remove":
                    extension_point.emit("extension_removed", plugin)

    def load_plugin(self, plugin_info: MrdPluginInfo):
        """
        Load a plugin.
        Note that this doesn't activate it, it is activated automatically
        when a extension point is loaded.

        It will also emit the ::extension_added signal for relevant ExtensionSets
        """
        plugin_info.active = True

    def unload_plugin(self, plugin_info: MrdPluginInfo):
        """
        Unload a plugin.
        Note that this relies on the ExtensionSet implementation to
        unload it as needed.

        It will emit the ::extension_removed signal for relevant ExtensionSets
        """
        plugin_info.active = False

    def handle_plugin_load_status_change(self, plugin_info: MrdPluginInfo, new_status: bool):
        """
        Handle changing of a plugin's active state, this is not what you should usually
        call to change it yourself, but a way for methods that change it to behave consistently
        by calling this method under-the-hood.

        You should not use this alone, as the `active` property of the plugin isn't affected
        """
        self._handle_extension_set_plug_signal("add" if new_status else "remove", plugin_info)


class MrdPluginInfo(GObject.Object):
    """
    Information about a plugin, abstracts the underlying object.
    You should not create this, plugin information objects are created
    by the plugin engine.

    attributes:
        dir: `str` the directory where the plugin is located
        type: the underlying class (type) that the plugin implementation uses
        u_activatable: `MrdPlugin` the underlying plugin object, you should
        use your loading calls on it as appropriate.
    properties:
        name: `str` the human-readable name of the plugin
        description: `str` the human-readable more-detailed description of the plugin
        module_name: `str` the machine name of the plugin (directory and python module)
        active: `bool` if the plugin should be used (is enabled)
        configurable: `bool` if the plugin has configuration settings
        built_in: `bool` if the plugin is built-in,
        built-in plugins are active by default and should not be
        disabled under normal circumstances
    """
    __gtype_name__ = "MrdPluginInfo"

    name = GObject.Property(type=str)
    description = GObject.Property(type=str)
    module_name = GObject.Property(type=str)

    built_in = GObject.Property(type=bool, default=False)

    def __init__(self, plugin_init: dict, plugin_engine: MrdPluginEngine):
        GObject.Object.__init__(self)
        self.plugin_engine = plugin_engine

        self.name = plugin_init["name"]
        self.description = plugin_init["description"]
        self.module_name = plugin_init["module"]
        self.built_in = plugin_init["built_in"]
        self.dir = os.path.join(self.plugin_engine.plugins_dir, self.module_name)

        self.type = None
        self.u_activatable = None
        self._active = self.built_in

        # Should be setup **before** importing the module for things like gresource
        # template definitions to work.
        self._gresource_path = Path(self.dir) / Path(f"{self.module_name}.gresource.xml")
        if os.path.isfile(self._gresource_path):
            self._setup_gresource()
        self._gresource = None

        # Finding the plugin object:
        # module_name is the name of the python module where it can be found,
        # and the plugin is the first one that subclasses MrdPlugin.
        # importlib.import_module doesn't take into consideration if the plugin has already been imported,
        # which causes redefinition issues with PyGObject GObjects
        plugin_module = __import__(f"mirdorph.plugins.{self.module_name}.{self.module_name}", fromlist=[''])
        for _, obj in inspect.getmembers(plugin_module):
            if inspect.isclass(obj) and issubclass(obj, MrdPlugin):
                self.type = obj
                self.u_activatable = obj()
                break
        if not self.type:
            raise Exception(f"couldn't find plugin in {self.module_name}")

    @GObject.Property(type=bool, default=False)
    def configurable(self):
        return self.u_activatable.get_configuration_widget() is not None

    @GObject.Property(type=bool, default=False)
    def active(self):
        return self._active

    @active.setter
    def active(self, value: bool):
        if value != self.active:
            self.plugin_engine.handle_plugin_load_status_change(self, value)
            self._active = value

    def _setup_gresource(self):
        """
        Attempt to load the plugin's gresource.

        The gresource is expected to be named <module_name>.gresource.xml in
        the plugin's directory.
        """
        compiled_gresource_path = Path(os.environ["XDG_CACHE_HOME"]) / Path(f"plugin-{self.module_name}.gresource")
        os.system(f"glib-compile-resources --sourcedir={self.dir} --target={compiled_gresource_path} {self._gresource_path}")
        self._gresource = Gio.Resource.load(str(compiled_gresource_path))
        self._gresource._register()

class MrdExtensionSet(GObject.Object):
    """
    The ExtensionSet is what is used for creating extension points in the appliocation.

    attributes:
        type: the class (type) of object that this extension requires.

    signals:
        extension_added: is emitted when a new plugin that satisfies the selected type
        should be loaded. You should load the extension in the signal handler
        extension_removed: is emmited when a plugin that satisfies the selected type should
        be unloaded. You should unload the extension in the signal handler

    For use information, consult your local documentation.
    """

    __gtype_name__ = "MrdExtensionSet"

    __gsignals__ = {
        "extension_added": (GObject.SignalFlags.RUN_FIRST, None,
                            (MrdPluginInfo,)),
        "extension_removed": (GObject.SignalFlags.RUN_FIRST, None,
                              (MrdPluginInfo,))
    }

    def __init__(self, engine: MrdPluginEngine, ext_type: type):
        """
        Create a new `MrdExtensionSet`.

        param:
            engine: the `MrdPluginEngine` of your application.
            ext_type: the base type that plugins for your extension point
            should implement.
        """
        GObject.Object.__init__(self)
        self._engine = engine
        self.type = ext_type

        self._engine.add_extension_point(self)

        self._compatible_plugins = [
            plugin for plugin in self._engine.get_enabled_plugins() if self._engine.is_plugin_compatible(plugin, self)
        ]

    def __iter__(self):
        return iter(self._compatible_plugins)

    def do_extension_added(self, plugin: MrdPluginInfo):
        self._compatible_plugins.append(plugin)

    def do_extension_removed(self, plugin: MrdPluginInfo):
        self._compatible_plugins.remove(plugin)


##############
# Plugin types
##############

class MrdPlugin(GObject.GObject):
    """
    The base plugin that all other plugins inherit from.
    You should not directly use this, it will be loaded
    unconditionally by all extension sets. Use a subclass.
    """

    def __init__(self):
        super().__init__()

    def load(self):
        """
        Load the plugin.
        Nothing should have been done in __init__ except init.
        All changes that your plugin does should be implemented here.
        """
        pass

    def unload(self):
        """
        Unload the plugin.
        This involves undoing everything you did in `load`
        """
        pass

    def get_configuration_widget(self) -> Gtk.Widget:
        """
        Get a widget contaniing the plugin's configuration settings,
        if it exists, else this doesn't return anything.
        """
        pass


class MrdApplicationPlugin(MrdPlugin):
    """
    A simple plugin that is loaded on application startup.
    """
    def __init__(self):
        super().__init__()


class MrdLoginMethodPlugin(MrdPlugin):
    """
    A plugin for login methods.

    Such a plugin has one task: to get the authentication token,
    it should emit the `token-obtained` signal with the token when
    authentication has been successfully completed.

    The plugin gets an area to add their login page/method widget, and access
    to the headerbar, for headerbar buttons.

    properties:
        headerbar: the `Adw.HeaderBar` of the login view, which preconfigures back
        button, window title, feel free to add buttons here.
        method_human_name: `str` the human readable name of the login method, for example
        "Graphical Login"
        is_primary: `bool` is this the primary log-in method? That is the easiest and recommended
        one which will be obviously displayed. Only one should exist.
    """
    __gsignals__ = {
        "token-obtained": (GObject.SignalFlags.RUN_FIRST, None,
                              (str,))
    }

    headerbar = GObject.Property(type=GObject.Object)
    method_human_name = GObject.Property(type=str)
    is_primary = GObject.Property(type=bool, default=False)

    def __init__(self):
        super().__init__()

    def load(self, login_method_cont):
        """
        Load the Login Method plugin.

        param:
            login_method_cont: `Adw.Bin` a container where you should add your
            widgets for this login method.
        """
        pass

    def unload(self, login_method_cont):
        """
        Unload the Login Method plugin.

        param:
            login_method_cont: `Adw.Bin` a container from which you should remove
            your widgets for this login method.
        """
        pass
