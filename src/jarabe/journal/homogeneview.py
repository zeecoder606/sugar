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

from sugar.graphics import style

from jarabe.journal.homogenetable import HomogeneTable
from jarabe.journal.sugarbin import SugarBin


class Cell(SugarBin):

    def __init__(self):
        SugarBin.__init__(self)

        self._fields = []
        self.fill_background(False)

    def add_field(self, field):
        self._fields.append(field)

    def fill_in(self, offset, metadata):
        # stub
        pass

    def do_fill_in(self, table, cell_index):
        metadata = table.get_metadata(cell_index)
        for i in self._fields:
            i.fill_in(metadata)
        self.fill_in(cell_index, metadata)

    def fill_background(self, selected):
        if selected:
            color = style.COLOR_HIGHLIGHT.get_gdk_color()
        else:
            color = style.COLOR_WHITE.get_gdk_color()
        self.modify_bg(gtk.STATE_NORMAL, color)
        for i in self._fields:
            if isinstance(i, gtk.TextView):
                i.modify_base(gtk.STATE_NORMAL, color)


class HomogeneView(HomogeneTable):

    __gsignals__ = {
            'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                                ([str])),
            }

    def __init__(self, selection, **kwargs):
        HomogeneTable.__init__(self, **kwargs)

        self._result_set = None

        self.editable = not selection
        self.cursor_visible = selection
        self.hover_selection = selection

    def set_result_set(self, result_set):
        if self._result_set is result_set:
            return

        self._result_set = result_set

        result_set_length = result_set.get_length()
        if self.cell_count == result_set_length:
            self.refill()
        else:
            self.cell_count = result_set_length

    def get_metadata(self, offset):
        self._result_set.seek(offset)
        return self._result_set.read()

    def do_highlight_cell(self, cell, selected):
        cell.fill_background(selected)
