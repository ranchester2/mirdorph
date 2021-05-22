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
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from enum import Enum

# Why a separate file?
# Because I want to test the parsing, but I can't really get pytest
# to import a python file with Gresource magic, so this must be generic.

class ComponentType(Enum):
    STANDARD = 0
    QUOTE = 1

def calculate_msg_parts(original_content: str) -> list:
    """
    Calculate and separate a list of types of components in a str message

    `returns:
        `list` of `tuple` where each tupple is (ComponentType, text: str)
    """

    components = []

    current_component_text = ""
    current_component_type = ComponentType.STANDARD
    for line in original_content.splitlines(keepends=True):
        if line.startswith("> "):
            if current_component_text and current_component_type != ComponentType.QUOTE:
                # Without this, before other parts we have a stupid blank line, (for example quotes)
                if current_component_type == ComponentType.STANDARD:
                    if current_component_text.endswith("\n"):
                        current_component_text = current_component_text[:-1]
                components.append(
                    (
                        copy.deepcopy(current_component_type),
                        copy.deepcopy(current_component_text)
                    )
                )
                current_component_text = ""
                current_component_type = None
            current_component_type = ComponentType.QUOTE
            current_component_text += line[2:]
        else:
            if current_component_text and current_component_type != ComponentType.STANDARD:
                # Without this, quotes will stupidly end with a blank line always
                if current_component_type == ComponentType.QUOTE:
                    if current_component_text.endswith("\n"):
                        current_component_text = current_component_text[:-1]

                components.append(
                    (
                        copy.deepcopy(current_component_type),
                        copy.deepcopy(current_component_text)
                    )
                )
                current_component_text = ""
                current_component_type = None
            current_component_type = ComponentType.STANDARD
            current_component_text += line
    if current_component_text:
        components.append(
            (
                copy.deepcopy(current_component_type),
                copy.deepcopy(current_component_text)
            )
        )

    return components


class MessageComponent(Gtk.Bin):
    def __init__(self, component_content: str, component_type: ComponentType, *args, **kwargs):
        Gtk.Bin.__init__(self, *args, **kwargs)
        self.component_type = component_type
        if self.component_type in [ComponentType.STANDARD, ComponentType.QUOTE]:
            self._text_label = Gtk.Label(
                wrap=True,
                wrap_mode=2,
                selectable=True,
                xalign=0.0
            )
            self._text_label.set_label(component_content)
            self._text_label.show()

            if self.component_type == ComponentType.QUOTE:
                self._text_label.get_style_context().add_class("quote")

            self.add(self._text_label)
