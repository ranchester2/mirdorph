# Significantly copied from GIARA and Gabmus's blog
import cairo
from gi.repository import Gtk, Gdk, GdkPixbuf

# What is this?
# This is a resizable picture widget, copied from Gabmus's blog and Giara.
# I tried to use it for the post images, however
# it really messed up scrolling no matter in what way I tried to implement it, so
# bye this


class AtkPicture(Gtk.DrawingArea):
    def __init__(self, path: str, governing_container: Gtk.Widget, max_width=450, *args, **kwargs):
        Gtk.DrawingArea.__init__(self, *args, **kwargs)
        self.path = path
        self.max_width = max_width
        self.governing_container = governing_container

        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.path)
        self.img_surface = Gdk.cairo_surface_create_from_pixbuf(
            self.pixbuf, 1, None
        )

    def get_useful_height(self, width):
        aw = width
        pw = self.pixbuf.get_width()
        ph = self.pixbuf.get_height()
        return aw/pw * ph

    def get_mscale_factor(self, width):
        return width / self.pixbuf.get_width()

    # Based on Fractal code
    # Adjust the `w` x `h` to fit in `maxw` x `maxh`, keeping the aspect ratio.
    def adjust_to(self, w: int, h: int, maxw: int, maxh: int) -> (int, int,):
        pw = w
        ph = h

        if pw > maxw:
            ph = maxw * ph / pw
            pw = maxw
        elif ph > maxh:
            pw = maxh * pw / ph
            ph = maxh

        return (pw, ph)

    def do_draw(self, context):
        width = self.get_allocated_width()
        if self.max_width > 0:
            if width > self.max_width:
                width = self.max_width

        width, height = self.adjust_to(
            width,
            self.get_useful_height(width),
            self.governing_container.get_allocation().width,
            self.governing_container.get_allocation().height,
        )


        sf = self.get_mscale_factor(width)
        context.scale(sf, sf)
        x_pos = ((self.get_allocated_width()//2)-(width//2))
        context.set_source_surface(self.img_surface, x_pos, 0)
        context.paint()
        self.set_size_request(-1, height)
