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

import gobject
import logging

import hippo

from sugar.graphics import style

from jarabe.journal.homogeneview import HomogeneView
from jarabe.journal.homogeneview import Cell
from jarabe.journal.widgets import *


class _Cell(Cell):

    def __init__(self):
        Cell.__init__(self)

        row = gtk.HBox()
        row.props.spacing = style.DEFAULT_SPACING
        self.add(row)

        self._keep = KeepIcon(box_width=style.GRID_CELL_SIZE)
        row.pack_start(self._keep, expand=False)

        self._icon = ObjectIcon(
                paint_box=False,
                pixel_size=style.STANDARD_ICON_SIZE)
        row.pack_start(self._icon, expand=False)

        self._title = Title()
        title_alignment = gtk.Alignment(
                xalign=0, yalign=0.5, xscale=1, yscale=0)
        title_alignment.add(self._title)
        row.pack_start(title_alignment)

        self._details = DetailsIcon()
        row.pack_end(self._details, expand=False)

        self._date = Timestamp()
        row.pack_end(self._date, expand=False)

        self._buddies = Buddies(buddies_max=3,
                xalign=0, yalign=0.5, xscale=1, yscale=0.15)
        row.pack_end(self._buddies, expand=False)

        self.show_all()

    def do_fill_in_cell_content(self, table, offset, metadata):
        self._keep.fill_in(metadata)
        self._icon.fill_in(metadata)
        self._title.fill_in(metadata)
        self._details.fill_in(metadata)
        self._date.fill_in(metadata)
        self._buddies.fill_in(metadata)


class ListView(HomogeneView):

    def __init__(self):
        HomogeneView.__init__(self, _Cell)
        self.frame_size = (None, 1)
        self.cell_size = (None, style.GRID_CELL_SIZE)
