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

    @property
    def padding_left(self):
        return self._padding_left

    @padding_left.setter
    def padding_left(self, value):
        if value == self._padding_left:
            return
        self._padding_left = value
        self.queue_resize()

    @property
    def padding_right(self):
        return self._padding_right

    @padding_right.setter
    def padding_right(self, value):
        if value == self._padding_right:
            return
        self._padding_right = value
        self.queue_resize()

    @property
    def padding_top(self):
        return self._padding_top

    @padding_top.setter
    def padding_top(self, value):
        if value == self._padding_top:
            return
        self._padding_top = value
        self.queue_resize()

    @property
    def padding_bottom(self):
        return self._padding_bottom

    @padding_bottom.setter
    def padding_bottom(self, value):
        if value == self._padding_bottom:
            return
        self._padding_bottom = value
        self.queue_resize()

    def set_padding(self, value):
        self._padding_left = value
        self._padding_right = value
        self._padding_top = value
        self._padding_bottom = value
        self.queue_resize()

    padding = property(None, set_padding)

    @property
    def x(self):
        return self._padding_left

    @property
    def y(self):
        return self._padding_top

    @property
    def width(self):
        return self.allocation.width - self._padding_left - self._padding_right

    @property
    def height(self):
        return self.allocation.height - self._padding_top - self._padding_bottom

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
