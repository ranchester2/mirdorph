import sys
# Workaround from stackoverflow to allow importing from src
sys.path.append("..")
from src.message_parsing import _process_links, _create_pango_markup

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
    
