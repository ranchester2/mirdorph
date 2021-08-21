You can create basic plugins for this (atleast you should in the future)

### Why not libpeas?

I iniitally tried to use libpeas, and it seemed to be a great solution, already
used by quite a few GNOME apps, no need to reinvent anything.

However I hit a major issue with how you basically have to define your own GObject
Ginterfaces, (it has a stupid assert to ensure that), and it isn't possible to do
that from Python.

So I reinvented the wheel, however it should still closely mimick that.

### Creating a plugin

There is an example "helloworld" plugin that is very basic and demonstrates
basic features.

To create a plugin, you should create it in the `mirdorph/plugins` directory,
first you need a .plugin file there, which looks like this

```json
{
	"name": "A Plugin",
	"module": "aplugin",
	"description": "An advanced Plugin",
	"built_in": false,
	"authors": [
		"Your Name"
	]
}
```

`name`, `module` and `description` are self-explanatory, however module is the name of the python
module where your plugin is defined, and the directory should also be named after it. The gresource
file also should be named after the module.

You should use meson to install all the required files.

The plugin class definition itself has to be a subclass of `MrdPlugin`, however you should use a fitting
subclass of it instead, and check its documentation for more specifics. For example for the most basic plugin
that justs loads at startup and exists on shutdown, you can use `MrdApplicationPlugin`.

An example would be

```python
from mirdorph.plugin import MrdApplicationPlugin

class HelloWorldPlugin(MrdApplicationPlugin):
    def __init__(self):
        super().__init__()
```

You should also implement the `load` and `unload` methods, and any additional ones that would be needed by the
specific type.

`load` should actually "enable" the plugin (__init__ shouldn't do that), like showing widgets, enabling functionality,
connecting signals. `unload` should undo **everything** that `load` does.

### Extension Sets

Extension sets are a similar concept to the ones in libpeas (however I am not sure since libpeas has basically zero documentation).

They are the extension points of the program, some objects have them, they specify the specific type of plugin that they support,
and then it is responsible for loading the plugins when it is notified that a compatible one has shown up/disapeared.

You can see a basic example in `main.py` with `MrdApplicationPlugin`

## CSS

I just realized I have no way of handling css or icons and stuff.
I guess I could technically just use standard gresurce and use css provider manually, but
I don't know, maybe I will just continue dumping it into the main project css file.
