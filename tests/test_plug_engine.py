import load_gtk
import sys
import pytest
import gi
# Workaround from stackoverflow to allow importing the program
sys.path.append("..")

from gi.repository import Gtk, Gio
from mirdorph.plugin import MrdPluginEngine, MrdExtensionSet, MrdPlugin


def test_plugin_discovery():
    engine = MrdPluginEngine()
    # We currently have atleast an example plugin
    plugins = engine.get_available_plugins()
    assert plugins


def test_plugin_load_unload():
    engine = MrdPluginEngine()
    for av_plugin in engine.get_available_plugins():
        # A plugin that is built-in won't be deactivated at first,
        # so we should ensure that.
        # and a for plugin that is (which we expect to exit), we can
        # test this here.
        if av_plugin.built_in:
            assert av_plugin.active
            av_plugin.active = False
        else:
            plugin = av_plugin

    assert not plugin.active
    assert not engine.get_enabled_plugins()
    engine.load_plugin(plugin)
    assert plugin.active
    assert engine.get_enabled_plugins()
    engine.unload_plugin(plugin)
    assert not plugin.active
    assert not engine.get_enabled_plugins()


def test_is_plugin_compatible():
    engine = MrdPluginEngine()
    plugin = engine.get_available_plugins()[0]
    engine.load_plugin(engine.get_available_plugins()[0])

    extension_set = MrdExtensionSet(
        engine,
        # Will be correct
        plugin.type
    )
    assert engine.is_plugin_compatible(plugin, extension_set)

    class FakePlugin(MrdPlugin):
        pass
    extension_set = MrdExtensionSet(
        engine,
        # Incompatible
        FakePlugin
    )
    assert not engine.is_plugin_compatible(plugin, extension_set)

def test_get_plugin_by_module():
    engine = MrdPluginEngine()
    plugin = engine.get_available_plugins()[0]

    plugin_by_mod_name = engine.get_plugin_from_module(plugin.module_name)

    assert plugin is plugin_by_mod_name

def test_extension_set_discovery():
    engine = MrdPluginEngine()
    plugin = engine.get_available_plugins()[0]
    engine.load_plugin(plugin)

    extension_set = MrdExtensionSet(
        engine,
        # Any plugin is ok
        plugin.type
    )
    assert list(extension_set)

    class FakePlugin(MrdPlugin):
        pass
    extension_set_wrong = MrdExtensionSet(
        engine,
        FakePlugin
    )
    assert not list(extension_set_wrong)


def test_extension_set_signals(mocker):
    engine = MrdPluginEngine()
    plugin = engine.get_available_plugins()[0]
    plugin.active = False
    extension_set = MrdExtensionSet(
        engine,
        plugin.type
    )

    mock = mocker.patch.object(extension_set, "emit")
    engine.load_plugin(plugin)
    mock.assert_called_with("extension_added", plugin)
    engine.unload_plugin(plugin)
    mock.assert_called_with("extension_removed", plugin)

def test_extension_state_change_via_property(mocker):
    # Signals are best as a showcase of the affects of enabling,
    # simply setting the active property (useful for binding) should
    # also do this.
    engine = MrdPluginEngine()
    plugin = engine.get_available_plugins()[0]
    plugin.active = False
    extension_set = MrdExtensionSet(
        engine,
        plugin.type
    )

    mock = mocker.patch.object(extension_set, "emit")
    plugin.active = True
    mock.assert_called_with("extension_added", plugin)
    plugin.active = False
    mock.assert_called_with("extension_removed", plugin)

def test_gresource(mocker):
    engine = MrdPluginEngine()

    # We don't need to load the plugin as gresources are created on initial startup.
    # At first I thought about doing it on load and undoing on unload, however then implementations
    # can't really define anything that uses gresources.
    # Helloworld example - "welcome_message.txt"
    assert Gio.resources_get_info("/org/gnome/gitlab/ranchester/Mirdorph/plugins/helloworld/welcome_message.txt", 0)
