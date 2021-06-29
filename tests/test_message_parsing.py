import sys
# Workaround from stackoverflow to allow importing from src
sys.path.append("..")

# Message parsing has gresource templates
import tests.load_gresource
from src.message_parsing import _process_links, _create_pango_markup, calculate_msg_parts, ComponentType

def test_process_links():
    test_text = """\
Test word https://google.com
Second line http://example.com"""
    expected_Text = """\
Test word <a href="https://google.com">https://google.com</a>
Second line <a href="http://example.com">http://example.com</a>"""

    assert _process_links(test_text) == expected_Text

def test_full_create_pango_markup():
    test_text = """\
Scary <b>non escaped markup</b>
with a link https://google.com
and other http://example.com"""
    expected_text = """\
Scary &lt;b&gt;non escaped markup&lt;/b&gt;
with a link <a href="https://google.com">https://google.com</a>
and other <a href="http://example.com">http://example.com</a>"""

    assert _create_pango_markup(test_text) == expected_text
    
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
