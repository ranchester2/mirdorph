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
import discord
import os
import sys
import subprocess
from pathlib import Path
from gi.repository import Gtk, Gio, GLib, Handy
from .channel_properties_window import ChannelPropertiesWindow
from .message_view import MessageView
from .message_entry_bar import MessageEntryBar
from .image_viewer import ImageViewer


@Gtk.Template(resource_path="/org/gnome/gitlab/ranchester/Mirdorph/ui/channel_inner_window.ui")
class ChannelInnerWindow(Gtk.Box):
    __gtype_name__ = "ChannelInnerWindow"

    _context_headerbar: Handy.HeaderBar = Gtk.Template.Child()

    _toplevel_content_stack: Gtk.Stack = Gtk.Template.Child()
    _empty_status_page: Handy.StatusPage = Gtk.Template.Child()

    _main_deck: Handy.Deck = Gtk.Template.Child()
    _channel_box: Gtk.Box = Gtk.Template.Child()

    _content_box: Gtk.Box = Gtk.Template.Child()

    _popout_button_stack: Gtk.Stack = Gtk.Template.Child()
    _popout_button: Gtk.Button = Gtk.Template.Child()
    _popin_button: Gtk.Button = Gtk.Template.Child()

    _context_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    _context_menu_popover: Gtk.PopoverMenu = Gtk.Template.Child()

    _flap_toggle_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, channel=None, empty=True, *args, **kwargs):
        """
        Create a new ChannelInnerWindow. NOTE: don't use this, use
        that of your application instead.

        NOTE: for correctly handling adaptiveness and folding, you need to
        connect ::notify::folded of your Flap yourself to `handle_flap_folding`.
        This is because we can't cleanly connect from __init__ here, as in some
        cases the main window isn't fully initialized yet.

        param:
            channel: channel id that this context uses (note: if none empty is on)
            empty: if this is just an empty state for its status message
        """
        
        Gtk.Box.__init__(self, *args, **kwargs)
        self.app = Gio.Application.get_default()
        self.channel_id = channel
        self.empty = empty
        if self.channel_id is None:
            self.empty = True

        self.is_poped = False

        if not self.empty:
            # Blocking
            self.channel_disc = asyncio.run_coroutine_threadsafe(
                self.app.discord_client.fetch_channel(self.channel_id),
                self.app.discord_loop
            ).result()

            self._context_headerbar.set_title("#" + self.channel_disc.name)
            if self.channel_disc.topic is not None:
                self._context_headerbar.set_subtitle(self.channel_disc.topic)

            self._image_viewer = ImageViewer(context=self)
            self._image_viewer.show()
            self._main_deck.add(self._image_viewer)

            self._message_view = MessageView(context=self)
            self._message_view.build_scroll()
            self._message_view.show()

            self._loading_history = False

            self._content_box.pack_start(self._message_view, True, True, 0)

            self._message_entry_bar = MessageEntryBar(context=self)
            self._message_entry_bar.show()

            self._msg_sending_scrl_mode_en = False

            self._content_box.pack_end(self._message_entry_bar, False, False, 0)
            self._content_box.pack_end(Gtk.Separator(visible=True), False, False, 0)

            self._context_action_group = Gio.SimpleActionGroup()
            prop_action = Gio.SimpleAction.new("properties", None)
            prop_action.connect("activate", self._on_channel_properties)
            self._context_action_group.add_action(prop_action)
            search_action = Gio.SimpleAction.new("search", None)
            search_action.connect("activate", self._on_channel_search)
            self._context_action_group.add_action(search_action)
            self.insert_action_group("context", self._context_action_group)
            context_menu_builder = Gtk.Builder.new_from_resource(
                "/org/gnome/gitlab/ranchester/Mirdorph/ui/context_menu.ui"
            )
            context_menu = context_menu_builder.get_object(
                "contextMenu"
            )
            self._context_menu_popover.bind_model(context_menu)


        elif self.empty:
            self._context_menu_button.destroy()
            self._popout_button.destroy()
            self._popin_button.destroy()
            self._popout_button_stack.destroy()
            self._toplevel_content_stack.set_visible_child(self._empty_status_page)

    # NOTE: not connected to the signal automatically, connect it yourself
    def handle_flap_folding(self, flap: Handy.Flap, *args):
        if flap.get_folded():
            self._flap_toggle_button.set_visible(True)
            self._popout_button_stack.set_visible(False)
            flap.set_swipe_to_close(True)

            self.popin()
        else:
            self._flap_toggle_button.set_visible(False)
            self._popout_button_stack.set_visible(True)
            flap.set_swipe_to_close(False)
        flap.set_swipe_to_open(True)

    # wrapper to load history in the messageview for message sending
    def load_history(self):
        self._message_view.load_history()

    # Could be better if this was defined in message_view instead?
    @property
    def is_loading_history(self):
        # Not using the spinner like before because .get_active()
        # seems undocumented and broken right now
        return self._loading_history

    def signify_loading_hs(self):
        self._loading_history = True

    def signify_stopped_loading_hs(self):
        self._loading_history = False

    @property
    def history_loading_is_complete(self):
        """
        Wrapper around message view's is history loading complete
        """

        return self._message_view.history_loading_is_complete


    def scroll_messages_to_bottom(self):
        """
        Scroll the view to the very bottom

        NOTE: you need to add to this box BEFORE you scroll
        if you wish to go to the real bottom
        """

        adj = self._message_view.scroller.get_vadjustment()
        adj.set_value(adj.get_upper())

    @property
    def is_scroll_at_bottom(self):
        """
        Is the user currently scrolled to the very bottom of the
        view
        """
        adj = self._message_view.scroller.get_vadjustment()
        # We can't check for it exactly, because if you scroll
        # for some reason it isn't the true bottom. So we use an "almost"
        # Also, we currently use this when showing the attachment bar

        # NOTE: for when attachment bar reveals, this for some reason doesn't
        # work with taller windows. However if I increase it it doesn't work at all!
        difference = abs(adj.get_value() - adj.get_upper())
        return difference < 600

    # Currently not used, initially intended for the revealer animation scrolling,
    # to disable it while scrolling. However that isn't needed
    @property
    def precise_is_scroll_at_bottom(self):
        """
        Is the scroll currently at the bottom (accurate mode)
        """
        adj = self._message_view.scroller.get_vadjustment()
        bottom = adj.get_upper() - adj.get_page_size()
        return (abs(adj.get_value() - bottom) < sys.float_info.epsilon)


    def popin(self):
        """
        Popin back to the main window
        """

        try:
            assert self._popout_window
        except AttributeError:
            logging.warning("attempted popin even though not popped out")
            return

        self._popout_button_stack.set_visible_child(self._popout_button)

        self._popout_window.remove(self)
        self._popout_window.destroy()
        # If we don't then the popin detection and folding breaks
        del(self._popout_window)

        self.app.main_win.unconfigure_popout_window(self)
        self.is_poped = False

        # If the image viewer is open and then poped out, or multiple poped in
        # while folding, this isn't updated.
        self._on_image_viewer_open_changed()

    # If you are here because of all the random CRITICAL Gtk
    # assertion warnings, I think you're in the wrong place.
    # they started appearing after 1860e9aff877a5493b2c9dbd4db0456ed0d61466
    # even though that changed NOTHING todo with popout
    def popout(self):
        """
        Popout the channel into a separate window
        """

        self.app.main_win.context_stack.remove(self)

        self.app.main_win.reconfigure_for_popout_window()

        self._popout_window = Handy.Window(
            default_width=650,
            default_height=470,
            icon_name="org.gnome.gitlab.ranchester.Mirdorph",
            title=f"Mirdorph - #{self.channel_disc.name}"
        )
        self._popout_window.connect("delete-event", lambda w, e : self.popin())
        self._popout_window.add(self)
        # For getting the focus
        self._message_entry_bar.handle_first_see()
        self._popout_window.present()
        self._popout_button_stack.set_visible_child(self._popin_button)
        self.is_poped = True

    def do_first_see(self):
        """
        Do actions when first selected for.

        This is similar to handle_first_see of the entry bar,
        currently the main functionality is making the user immediatly
        able to type in the message entry
        """
        self._message_entry_bar.handle_first_see()

    def prepare_scroll_for_msg_send(self):
        """
        Schedule next message to cause screen to scroll
        """
        self._msg_sending_scrl_mode_en = True

    def unprepare_scroll_for_msg_send(self):
        """
        Disable mode of scheduling next messages to cause
        screen to scroll
        """
        self._msg_sending_scrl_mode_en = False

    def start_attachment_reveal_scroll_mode(self):
        """
        Start the scroll mode for while the attachment tray is revealing,
        This is for smooth animation on all window sizes
        """
        self._message_view._attachment_tray_scroll_revealment_mode = True

    def end_attachment_reveal_scroll_mode(self):
        """
        End the scroll mode for while the attachment tray is revealing,
        This is for smooth animation on all window sizes
        """
        self._message_view._attachment_tray_scroll_revealment_mode = False

    @property
    def is_scroll_for_msg_send(self):
        """
        Wether currently the next received message is expected to be
        the one sent by the user, and it is expected that the view
        is scrolled to their message
        """
        return self._msg_sending_scrl_mode_en

    @Gtk.Template.Callback()
    def _on_popout_context_button_clicked(self, button):
        self.popout()

    @Gtk.Template.Callback()
    def on_popin_context_button_clicked(self, button):
        self.popin()

    @Gtk.Template.Callback()
    def _on_flap_toggle_button_clicked(self, button):
        self.app.main_win.main_flap.set_reveal_flap(
            not self.app.main_win.main_flap.get_reveal_flap()
        )

    @Gtk.Template.Callback()
    def _on_image_viewer_open_changed(self, *args):
        # The flap should be made invisible when we open the image viewer,
        # however only when not popped out.

        # Cases of resizing the window to pop in popped out windows are handled
        # by calling this on pop in.
        if not self.is_poped:
            if self._main_deck.get_visible_child() == self._channel_box:
                self.app.main_win.main_flap.set_fold_policy(
                    Handy.FlapFoldPolicy.AUTO
                )
                # If this is not checked, if the flap is made folded
                # while popout windows exist that are being popped in,
                # the flap is revealed which is unexpected.
                if not self.app.main_win.main_flap.get_folded():
                    self.app.main_win.main_flap.set_reveal_flap(True)

                # May be unset after disable swipe to open
                self.handle_flap_folding(self.app.main_win.main_flap)
            elif self._main_deck.get_visible_child() == self._image_viewer:
                self.app.main_win.main_flap.set_fold_policy(
                    Handy.FlapFoldPolicy.NEVER
                )
                self.app.main_win.main_flap.set_reveal_flap(False)
                # Sometime it is possible to have it appear
                # via swipe back.
                self.app.main_win.main_flap.set_swipe_to_open(False)

    def _on_channel_properties(self, action, param):
        properties_window = ChannelPropertiesWindow(channel=self.channel_disc)
        properties_window.set_modal(True)
        if self.is_poped:
            properties_window.set_transient_for(self._popout_window)
        else:
            properties_window.set_transient_for(self.app.main_win)
        properties_window.present()

    def _on_channel_search(self, action, param):
        # placeholder
        print(f"channel search for {self.channel_disc.name}")

    def show_image_viewer(self, attachment: discord.Attachment):
        """
        Show the image viewer/diretory for this channel

        param:
            attachment: show a given attachment at start
        """
        self._image_viewer.display_image(attachment)
        self._main_deck.set_visible_child(self._image_viewer)

    def exit_image_viewer(self):
        """
        Helper function to exit the image viewer from within,
        for example: for back buttons.
        """
        self._main_deck.set_visible_child(self._channel_box)
