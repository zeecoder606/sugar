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
from sugar.graphics.roundbox import CanvasRoundBox

from jarabe.journal.homogenetable import VHomogeneTable


class Cell(gtk.EventBox):

    def __init__(self):
        gtk.EventBox.__init__(self)
        self.select(False)

    def do_fill_in_cell_content(self, table, offset, metadata):
        # needs to be overriden
        pass

    def do_fill_in(self, table, cell_index):
        result_set = table.get_result_set()
        result_set.seek(cell_index)
        self.do_fill_in_cell_content(table, cell_index, result_set.read())
        if table.hover_selection:
            self.select(table.cursor == cell_index)

    def select(self, selected):
        if selected:
            self.modify_bg(gtk.STATE_NORMAL,
                    style.COLOR_SELECTION_GREY.get_gdk_color())
        else:
            self.modify_bg(gtk.STATE_NORMAL,
                    style.COLOR_WHITE.get_gdk_color())


class HomogeneView(VHomogeneTable):

    __gsignals__ = {
            'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                                ([str])),
            }

    def __init__(self, cell_class, **kwargs):
        assert(issubclass(cell_class, Cell))

        VHomogeneTable.__init__(self, cell_class, **kwargs)

        self._result_set = None
        self.hover_selection = False

        self.connect('cursor-changed', self.__cursor_changed_cb)

    def get_result_set(self):
        return self._result_set

    def set_result_set(self, result_set):
        if self._result_set is result_set:
            return

        self._result_set = result_set

        result_set_length = result_set.get_length()
        if self.cell_count == result_set_length:
            self.refill()
        else:
            self.cell_count = result_set_length

    def __cursor_changed_cb(self, table, old_cursor):
        if not self.hover_selection:
            return
        old_cell = table[old_cursor]
        if old_cell is not None:
            old_cell.select(False)
        new_cell = table[table.cursor]
        if new_cell is not None:
            new_cell.select(True)
