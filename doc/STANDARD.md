Mirdorph is a (bad) Discord client utilizing discord.py and GTK3.

## How interaction with discord

First, discord with an asyncio loop runs in the main thread, GTK runs
in a separate thread from the very start, however that doesn't mean
we cannot communicate.

To run discord code from GTK:

use asyncio.run_coroutine_threadsafe:

```python3
import asyncio

asyncio.run_coroutine_threadsafe(
    discord_client.do_something(),
    discord_loop
)
```

`discord_loop` and `discord_client` are also attributes of the GtkApplication.
You can get the return value from this with `.result()` (note: is blocking).

To launch code in Gtk from an async function you pass to the run coroutine thing,
you can use `GLib.idle_add(func, *args)`.

Now, the other way round:

There isn't really a reason to do this asside from listening to events, and that is simple.

```python3
from .event_receiver import EventReceiver

class YourObject(EventReceiver):
    def __init__(self):
        EventReceiver.__init__(self)

    def disc_on_message(self, message):
        print(message.content)
```

Simply subclass EventReceiver and you will be able to get any Discord event with
`disc_` + the generic event name from the discord.py documentation.

NOTE: make sure to run discord stuff with asyncio.run_coroutine_threadsafe.
and that is about it with interaction.

## Main architect

The main thing is that any channel/room is a `ChannelInnerWindow` and commonly
refered to as a `context`. The context holds everything needed about a discord channel.
And usually has an integrated `MessageView` which is the thingy that displays the
messages.

The objects are themselves meant to keep themselves in sync with their on-discord state.

Messageview at it's heart uses a GtkListBox, with children like message representations with
`MessageWidget`, and is sorted automatically, you don't have to worry about that.

A context itself is a Gtk widget too, and is the whole headerbar+area thing you see
on the left. The popoit windows are simpy a `ChannelInnerWindow` inside a `AdwWindow`.

Global state is application, yada yada, etc. There are quite a few things like that

Also `ConfMan` is used for configuration, the application has an instance of it as an
attribute. Simply use `confman.get_value("example")` or
`confman.set_value("new_value", data)`.