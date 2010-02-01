# Copyright (C) 2010, Aleksey Lim
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gobject


class SugarBin(gtk.EventBox):

    def __init__(self, **kwargs):
        gtk.EventBox.__init__(self, **kwargs)

        self._padding_left = 0
        self._padding_right = 0
        self._padding_top = 0
        self._padding_bottom = 0

    def get_padding_left(self):
        return self._padding_left

    def set_padding_left(self, value):
        if value == self._padding_left:
            return
        self._padding_left = value
        self.queue_resize()

    padding_left = gobject.property(
            getter=get_padding_left, setter=set_padding_left)

    def get_padding_right(self):
        return self._padding_right

    def set_padding_right(self, value):
        if value == self._padding_right:
            return
        self._padding_right = value
        self.queue_resize()

    padding_right = gobject.property(
            getter=get_padding_right, setter=set_padding_right)

    def get_padding_top(self):
        return self._padding_top

    def set_padding_top(self, value):
        if value == self._padding_top:
            return
        self._padding_top = value
        self.queue_resize()

    padding_top = gobject.property(
            getter=get_padding_top, setter=set_padding_top)

    def get_padding_bottom(self):
        return self._padding_bottom

    def set_padding_bottom(self, value):
        if value == self._padding_bottom:
            return
        self._padding_bottom = value
        self.queue_resize()

    padding_bottom = gobject.property(
            getter=get_padding_bottom, setter=set_padding_bottom)

    def set_padding(self, value):
        self._padding_left = value
        self._padding_right = value
        self._padding_top = value
        self._padding_bottom = value
        self.queue_resize()

    padding = gobject.property(setter=set_padding)

    # TODO later props are intended only only padding* but
    # for future border* as well

    def get_x(self):
        return self._padding_left

    x = gobject.property(getter=get_x)

    def get_y(self):
        return self._padding_top

    y = gobject.property(getter=get_y)

    def get_width(self):
        return self.allocation.width - self._padding_left - self._padding_right

    width = gobject.property(getter=get_width)

    def get_height(self):
        return self.allocation.height - self._padding_top - self._padding_bottom

    height = gobject.property(getter=get_height)

    # gtk.Widget overrides

    def get_pointer(self):
        x, y = gtk.EventBox.get_pointer(self)
        return (x - self.x, y - self.y)

    def do_size_request(self, requisition):
        if self.child is not None:
            requisition.width, requisition.height = self.child.size_request()
        else:
            requisition.width, requisition.height = (0, 0)
        requisition.width += self._padding_left + self._padding_right
        requisition.height += self._padding_top + self._padding_bottom

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

        if self.child is not None:
            __, __, width, height = allocation
            child_allocation = gtk.gdk.Rectangle(
                    x=self._padding_left, y=self._padding_top,
                    width=width - self._padding_left - self._padding_right,
                    height=height - self._padding_top - self._padding_bottom)
            child_allocation.width = max(0, child_allocation.width)
            child_allocation.height = max(0, child_allocation.height)
            self.child.size_allocate(child_allocation)

gobject.type_register(SugarBin)
