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

from sugar.graphics import style

from jarabe.journal.homogeneview import HomogeneView
from jarabe.journal.homogeneview import Cell
from jarabe.journal.fields import *


class _Cell(Cell):

    def __init__(self):
        Cell.__init__(self)

        row = gtk.HBox()
        row.props.spacing = style.DEFAULT_SPACING
        self.add(row)

        keep = KeepIcon()
        row.pack_start(keep, expand=False)
        self.add_field(keep)

        icon = ObjectIcon(
                paint_box=False,
                pixel_size=style.STANDARD_ICON_SIZE)
        row.pack_start(icon, expand=False)
        self.add_field(icon)

        title = Title()
        title_alignment = gtk.Alignment(
                xalign=0, yalign=0.5, xscale=1, yscale=0)
        title_alignment.add(title)
        row.pack_start(title_alignment)
        self.add_field(title)

        details = DetailsIcon()
        row.pack_end(details, expand=False)
        self.add_field(details)

        date = Timestamp()
        row.pack_end(date, expand=False)
        self.add_field(date)

        buddies = Buddies(buddies_max=3,
                xalign=0, yalign=0.5, xscale=1, yscale=0.15)
        row.pack_end(buddies, expand=False)
        self.add_field(buddies)

        self.show_all()


class ListView(HomogeneView):

    def __init__(self, selection):
        HomogeneView.__init__(self, selection)
        self.frame_size = (None, 1)
        self.cell_size = (None, style.GRID_CELL_SIZE)

    def do_cell_new(self):
        return _Cell()
