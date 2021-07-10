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

import copy
import logging
import re
import gi
import html2pango
import mistune
from gi.repository import Adw, Gtk, Pango
from enum import Enum
from .link_preview import LinkPreviewExport


class ComponentType(Enum):
    STANDARD = 0
    QUOTE = 1


def calculate_msg_parts(original_content: str) -> list:
    """
    Calculate and separate a list of types of components in a str message.

    This isn't low-level formatting stuff, and discord mentions for example,
    but top-level stuff like separating quotes out, and probably in the future
    codeblocks.

    returns:
        `list` of `tuple` where each tupple is (ComponentType, text: str)
    """
    components = []

    # NOTE: components is a mutable list
    def reset_last_component(current_component_type: ComponentType, current_component_text: str,
                             new_component_type: ComponentType, components: list) -> bool:
        if current_component_text and current_component_type != new_component_type:
            # Without this, before other parts we have a stupid blank line, (for example quotes)
            # For now for all types, and probably for all future ones we also will need this
            if current_component_text.endswith("\n"):
                current_component_text = current_component_text[:-1]
            components.append(
                (
                    copy.deepcopy(current_component_type),
                    copy.deepcopy(current_component_text)
                )
            )
        # Is this really a new component and we should reset the counter?
            return True
        return False

    current_component_text = ""
    current_component_type = ComponentType.STANDARD
    for line in original_content.splitlines(keepends=True):
        if line.startswith("> ") or line.startswith(">>> "):
            if reset_last_component(current_component_type, current_component_text, ComponentType.QUOTE, components):
                current_component_text = ""
                current_component_type = None

            current_component_type = ComponentType.QUOTE

            # We don't put the > into the output, because
            # it is expected to handle that manually after the fact
            amount = len("> ")
            if line.startswith(">>>"):
                amount = len(">>> ")
            current_component_text += line[amount:]
        else:
            if reset_last_component(current_component_type, current_component_text, ComponentType.STANDARD, components):
                current_component_text = ""
                current_component_type = None
            current_component_type = ComponentType.STANDARD
            current_component_text += line

    # When the loop ends, we also need to add the last one
    if current_component_text:
        components.append(
            (
                copy.deepcopy(current_component_type),
                copy.deepcopy(current_component_text)
            )
        )

    return components


def _extract_discord_components(message_string) -> list:
    """
    Extract the discord-specific components of a string.
    Returns a list of tuples. Where each tuple is:
        0 - discord component type
        1 - the data of the component
        2 - range of chars of the original message string that are the
        extracted component

    List empty if none exist
    """
    # Not immplemented for now, need to figure out embeding widgets in labels.
    return []


def _generate_exports(message_string: str):
    links = re.findall(r"(?P<url>https?://[^\s]+)", message_string)
    return []
    return [LinkPreviewExport(link) for link in links]


def _create_pango_markup(message_string: str) -> str:
    html_base = mistune.html(html2pango.html_escape(message_string))
    workd_on_str = html2pango.markup_from_raw(html_base)

    return workd_on_str


def build_widget_list(message_string: str) -> list:
    """
    Build a widget list for a part of text in a discord message.
    List elements can be either a string of pango markup, or
    a custom Gtk Widget

    returns:
        A list of either `Gtk.Widget` or `str`
    """
    # Discord components need to be parsed before converting the strings
    # to pango.
    discord_components = _extract_discord_components(message_string)
    if discord_components:
        pass

    widget_list = []
    widget_list.append(_create_pango_markup(message_string))

    return widget_list


class MessageComponent(Adw.Bin):
    def __init__(self, component_content: str, component_type: ComponentType, *args, **kwargs):
        Adw.Bin.__init__(self, *args, **kwargs)
        self.component_type = component_type
        self._raw_component_content = component_content
        # Exports are based on non-sescaped, non-processed content
        self.exports = _generate_exports(self._raw_component_content)

        if self.component_type in [ComponentType.STANDARD, ComponentType.QUOTE]:
            self._text_label = Gtk.Label(
                wrap=True,
                wrap_mode=Pango.WrapMode.WORD_CHAR,
                selectable=True,
                xalign=0.0
            )
            # Safe currently as only strings
            self._text_label.set_markup("".join(build_widget_list(self._raw_component_content)))

            if self.component_type == ComponentType.QUOTE:
                self._text_label.add_css_class("quote")

            self.set_child(self._text_label)
