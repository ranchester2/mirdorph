# Mirdorph - a crappy low feature Discord Client

That is it, and it uses discord.py and GTK3.

To run:

Have flatpak installed.
Install `org.gnome.Sdk` (I am not sure if you need to do that manually on a
fresh install, but get it from flathub just in case)

And from the source directory:

```bash
# To build and install
flatpak-builder --force-clean --user --install build-dir org.gnome.gitlab.ranchester.Mirdorph.json
# To run
flatpak run org.gnome.gitlab.ranchester.Mirdorph
```

Here are a few screenshots of 0.0.1:

![image](./doc/asset/mirdorph-login.png)
![image](./doc/asset/mirdorph-login-token.png)
![image](./doc/asset/mirdorph-unselected-main-win.png)
![image](./doc/asset/mirdorph-with-channel.png)
![image](./doc/asset/mirdorph-popped-out.png)
![image](./doc/asset/mirdorph-mobile.png)
![image](./doc/asset/mirdorph-mobile-with-sidebar.png)
