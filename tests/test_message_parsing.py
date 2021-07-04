import sys
# Workaround from stackoverflow to allow importing from src
sys.path.append("..")

# Message parsing has gresource templates, and linkpreview uses handy
import tests.load_gtk
from src.link_preview import LinkPreviewExport
from src.message_parsing import _create_pango_markup, calculate_msg_parts, _generate_exports, ComponentType

def test_create_pango_markup_links():
    test_text = """\
with a link https://google.com
and other http://example.com"""
    expected_text = """\
with a link <a href="https://google.com">https://google.com</a>
and other <a href="http://example.com">http://example.com</a>"""

    assert _create_pango_markup(test_text) == expected_text

def test_create_pango_markup_escaping():
    test_text = """\
spooky <b>non escaped</b>
<a href="hello">other</a>"""
    expected_text = """\
spooky &lt;b&gt;non escaped&lt;/b&gt;
&lt;a href=&quot;hello&quot;&gt;other&lt;/a&gt;"""

    assert _create_pango_markup(test_text) == expected_text

# Why not test all of markdown? Because html2pango has tests in itself.

def test_calculate_message_parts():
    example_message = """\
Hello, this is a test message
> That has a quote
> And it continues
> Almost forever
Until it suddenly stops and you don't
know what to do.
However the bot said that:
>>> No this doesn't make any sense."""

    correct_components = [
        (
            ComponentType.STANDARD,
            "Hello, this is a test message"
        ),
        (
            ComponentType.QUOTE,
            "That has a quote\nAnd it continues\nAlmost forever"
        ),
        (
            ComponentType.STANDARD,
            "Until it suddenly stops and you don't\nknow what to do.\nHowever the bot said that:"
        ),
        (
            ComponentType.QUOTE,
            "No this doesn't make any sense."
        )
    ]

    components = calculate_msg_parts(example_message)

    assert correct_components == components

