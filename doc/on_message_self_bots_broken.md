The various `on_message_*` events are broken in self bots in Discord.py since
a few days ago.

For example, the .content and .embeds don't work, unless they are messages that you sent!

Luckily, messages retrieved through .history() still work!

This basically solves the `on_message` use case, but for editing
we can't really get the before now, only the after. (But who needs before anyways?)

I really hope Discord doesnt continue breaking this.

But I have patched discord.py to allways retrieve `on_message` from history.
You can find it in the /patches directory.

