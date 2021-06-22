# Significantly copied from GIARA and Gabmus's blog
import cairo
from gi.repository import Gtk, Gdk, GdkPixbuf

# What is this?
# This is a resizable picture widget, copied from Gabmus's blog and Giara.
# I tried to use it for the post images, however
# it really messed up scrolling no matter in what way I tried to implement it, so
# bye this


class AtkPicture(Gtk.DrawingArea):
    def __init__(self, path: str, max_width=450, *args, **kwargs):
        Gtk.DrawingArea.__init__(self, *args, **kwargs)
        self.path = path
        self.max_width = max_width

        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.path)
        self.img_surface = Gdk.cairo_surface_create_from_pixbuf(
            self.pixbuf, 1, None
        )
        self.old_scaled_surface = None
        self.old_sf = -1

    def get_useful_height(self, width):
        aw = width
        pw = self.pixbuf.get_width()
        ph = self.pixbuf.get_height()
        return aw/pw * ph

    def get_mscale_factor(self, width):
        return width / self.pixbuf.get_width()

    def do_draw(self, context):
        width = self.get_allocated_width()
        x_pos = 0
        if self.max_width > 0:
            if width > self.max_width:
                width = self.max_width
                x_pos = (self.get_allocated_width()//2)-(width//2)
        height = self.get_useful_height(width)
        sf = self.get_mscale_factor(width)
        if sf != self.old_sf:
            self.old_sf = sf
            wsf = self.get_scale_factor()
            self.old_scaled_surface = context.get_target().create_similar(
                cairo.Content.COLOR_ALPHA,
                int(wsf*width),
                int(wsf*height)
            )
            self.old_scaled_surface.set_device_scale(wsf, wsf)
            scaled_ctx = cairo.Context(self.old_scaled_surface)
            scaled_ctx.scale(sf, sf)
            scaled_ctx.set_source_surface(self.img_surface, x_pos, 0)
            scaled_ctx.paint()
        context.set_source_surface(self.old_scaled_surface, x_pos, 0)
        context.paint()
        self.set_size_request(-1, height)
