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
import logging

from jarabe.journal.homogeneview import HomogeneView
from jarabe.journal.homogeneview import Cell
from jarabe.journal.widgets import *


TOOLBAR_WIDTH = 20

THUMB_WIDTH = 240
THUMB_HEIGHT = 180

TEXT_HEIGHT = gtk.EventBox().create_pango_layout('W').get_pixel_size()[1]

CELL_WIDTH = THUMB_WIDTH + TOOLBAR_WIDTH + style.DEFAULT_PADDING + \
             style.DEFAULT_SPACING
CELL_HEIGHT = THUMB_HEIGHT + TEXT_HEIGHT * 3 + style.DEFAULT_PADDING * 3 + \
              style.DEFAULT_SPACING


class _Cell(Cell):

    def __init__(self):
        Cell.__init__(self)

        cell = gtk.HBox()
        self.add(cell)

        # toolbar

        toolbar = gtk.VBox()
        cell.pack_start(toolbar, expand=False)

        self._keep = KeepIcon(
                box_width=style.GRID_CELL_SIZE)
        toolbar.pack_start(self._keep, expand=False)

        self._details = DetailsIcon()
        toolbar.pack_start(self._details, expand=False)

        # thumb

        main = gtk.VBox()
        cell.pack_end(main)

        #thumb = Thumb()
        #main.pack_end(thumb)

        # text

        text = gtk.VBox()
        main.pack_end(text, expand=False)

        self._title = Title(
                max_line_count=2,
                xalign=0, yalign=0, xscale=1, yscale=0)
        text.pack_start(self._title)

        self._date = Timestamp(
                xalign=0.0,
                ellipsize=pango.ELLIPSIZE_END)
        text.pack_end(self._date, expand=False)

        self.show_all()

    def do_fill_in_cell_content(self, table, metadata):
        self._keep.check_out(metadata)
        self._details.check_out(metadata)
        self._title.check_out(metadata)
        self._date.check_out(metadata)


class ThumbsView(HomogeneView):

    def __init__(self):
        HomogeneView.__init__(self, _Cell)

    def do_size_allocate(self, allocation):
        column_count = gtk.gdk.screen_width() / CELL_WIDTH
        row_count = gtk.gdk.screen_height() / CELL_HEIGHT
        self.frame_size = (row_count, column_count)

        HomogeneView.do_size_allocate(self, allocation)
