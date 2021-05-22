import sys
import pytest
# Workaround from stackoverflow to allow importing from src
sys.path.append("..")

from src.message_parsing import calculate_msg_parts, ComponentType

def test_calculate_basic():
    example_message = """\
Hello, this is a test message
> That has a quote
> And it continues
> Almost forever
Until it suddenly stops and you don't
know what to do.
However he said that:
> No this doesn't make any sense.
> You're wrong!"""

    correct_components = [
        (
            ComponentType.STANDARD,
            "Hello, this is a test message\n"
        ),
        (
            ComponentType.QUOTE,
            "That has a quote\nAnd it continues\nAlmost forever\n"
        ),
        (
            ComponentType.STANDARD,
            "Until it suddenly stops and you don't\nknow what to do.\nHowever he said that:\n"
        ),
        (
            ComponentType.QUOTE,
            "No this doesn't make any sense.\nYou're wrong!"
        )
    ]

    components = calculate_msg_parts(example_message)

    assert correct_components == components