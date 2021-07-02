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
import discord
import sys
from gi.repository import Gtk, Gio, Handy
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
            # Get channels works because guilds are already chunked when the UI
            # for creating a context appears.
            self.channel_disc = self.app.discord_client.get_channel(self.channel_id)

            self._context_headerbar.set_title("#" + self.channel_disc.name)
            if self.channel_disc.topic is not None:
                self._context_headerbar.set_subtitle(self.channel_disc.topic)

            self._image_viewer = ImageViewer(context=self)
            self._image_viewer.show()
            self._main_deck.add(self._image_viewer)

            self._message_view = MessageView(context=self)
            self._message_view.show()
            # It is needed to check if now the scroll should be handled differently
            # if for example the user just sent a message, for example to
            # always scroll to the bottom then.
            # Users are expected to directly read, set, and get this attribute.
            self.scroll_for_msg_send = False
            self._content_box.pack_start(self._message_view, True, True, 0)

            self._message_entry_bar = MessageEntryBar(context=self)
            self._message_entry_bar.show()
            # If the attachment tray "revealment" mode for handling scrolling is
            # used (smooth animation), users of this are expected to directly set it
            self.attachment_tray_scroll_mode = False
            self._content_box.pack_end(self._message_entry_bar, False, False, 0)
            self._content_box.pack_end(Gtk.Separator(visible=True), False, False, 0)

            self._msg_sending_scrl_mode_en = False

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
            # Expected that going into "mobile mode" unpops
            # all the popped out windows.
            self.popin()
        else:
            self._flap_toggle_button.set_visible(False)
            self._popout_button_stack.set_visible(True)
            flap.set_swipe_to_close(False)
        flap.set_swipe_to_open(True)

    def load_history(self):
        """
        Load the initial history view, designed for
        when first displaying.
        """
        self._message_view.load_history()

    def scroll_messages_to_bottom(self):
        """
        Scroll the view to the very bottom

        For example, when you send a message it is useful to
        see it.
        """
        adj = self._message_view.scroller.get_vadjustment()
        adj.set_value(adj.get_upper())

    @property
    def is_scroll_at_bottom(self):
        """
        Is the scroll currently at the very bottom
        """
        adj = self._message_view.scroller.get_vadjustment()
        bottom = adj.get_upper() - adj.get_page_size()
        return (abs(adj.get_value() - bottom) < sys.float_info.epsilon)

    def popin(self):
        """
        Popin back to the main window
        """
        if not self.is_poped:
            logging.warning("attempted popin even though not popped out")
            return

        self._popout_button_stack.set_visible_child(self._popout_button)

        self._popout_window.remove(self)
        self._popout_window.destroy()

        self.app.main_win.unconfigure_popout_window(self)
        self.is_poped = False

        # If the image viewer is open and then poped out, or multiple poped in
        # while folding, this isn't updated.
        self._on_image_viewer_open_changed()

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
        self.do_first_see()
        self._popout_window.present()

        self._popout_button_stack.set_visible_child(self._popin_button)
        self.is_poped = True

    def do_first_see(self):
        """
        Do actions for when switched to/displayed.

        For example, make the message entry bar focused
        when switching to this channel.
        """
        self._message_entry_bar.handle_first_see()

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
