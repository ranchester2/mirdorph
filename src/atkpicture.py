import cairo
from gi.repository import Gtk, Gdk, GdkPixbuf

# What is this?
# This is a resizable picture widget, copied from Gabmus's blog and Giara.
# Unfortunatley it was eventually left unused.
# It really messed up scrolling no matter in what way I tried to implement it, so
# by this

class AtkPicture(Gtk.DrawingArea):
    __gtype_name__ = "AtkPicture"

    def __init__(self, path, confman, template=False, width=None, height=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.confman = confman
        self.path = path

        if not template:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.path)
        else:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_resource_at_scale(self.path, width, height, preserve_aspect_ratio=False)
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
        max_wid = self.confman.get_value('max_image_content_width')
        if self.pixbuf.get_width() < 100:
            max_wid /= max_wid / 3
    
        if max_wid > 0:
            if width > max_wid:
                width = max_wid
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