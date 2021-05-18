The various `on_message_*` events are broken in self bots in Discord.py since
a few days ago.

For example, the .content and .embeds don't work, unless they are messages that you sent!

Luckily, messages retrieved through .history() still work!

This basically solves the `on_message` use case, but for editing
we can't really get the before now, only the after. (But who needs before anyways?)

I really hope Discord doesnt continue breaking this.

But I have patched discord.py to allways retrieve `on_message` from history.
You can find it in the /patches directory.

UPDATE:

There are now kind of real solutions to this, the most promissing is this fork
of discord.py doiflies https://github.com/dolfies/discord.py-self. It originally
fixed the issue of .content and .embeds, has some other things now and more.

I have backported the fix from it to a nicely formatted patch, and now use
that to fix `on_message` and similar, note that it uses "Lazy Users` in some places.

I think the community for this is good enough so that this project isn't
likely to suffer a fate worse than death.
