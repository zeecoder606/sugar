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

        self._row = gtk.HBox()
        self._row.props.spacing = style.DEFAULT_SPACING
        self.add(self._row)

        keep = KeepIcon(box_width=style.GRID_CELL_SIZE)
        self._row.pack_start(keep, expand=False)

        icon = ObjectIcon(size=style.STANDARD_ICON_SIZE)
        self._row.pack_start(icon, expand=False)

        title = Title(xalign=0, yalign=0.5, xscale=1, yscale=0)
        self._row.pack_start(title)

        details = DetailsIcon()
        self._row.pack_end(details, expand=False)

        date = Timestamp()
        self._row.pack_end(date, expand=False)

        buddies = Buddies(buddies_max=3,
                xalign=0, yalign=0.5, xscale=1, yscale=0.15)
        self._row.pack_end(buddies, expand=False)

        self.show_all()

    def do_fill_in_cell_content(self, table, offset, metadata):
        for i in self._row.get_children():
            i.fill_in(metadata)


class ListView(HomogeneView):

    def __init__(self):
        HomogeneView.__init__(self, _Cell)
        self.frame_size = (None, 1)
        self.cell_size = (None, style.GRID_CELL_SIZE)
