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
from jarabe.journal import preview
from jarabe.journal import entry


class _Cell(Cell):

    def __init__(self):
        Cell.__init__(self)

        self._last_thumb_uid = None
        self._last_thumb_offset = None
        self._last_thumb_mtime = None

        cell = gtk.HBox()
        cell.props.border_width = style.DEFAULT_PADDING
        self.add(cell)

        # toolbar

        toolbar = gtk.VBox()
        cell.pack_start(toolbar, expand=False)

        self._keep = KeepIcon()
        toolbar.pack_start(self._keep, expand=False)

        self._details = DetailsIcon()
        toolbar.pack_start(self._details, expand=False)

        # main

        main = gtk.VBox()
        main.props.spacing = style.DEFAULT_PADDING
        cell.pack_end(main)

        self._icon = ObjectIcon(pixel_size=style.MEDIUM_ICON_SIZE)
        self._icon.set_size_request(preview.THUMB_WIDTH, preview.THUMB_HEIGHT)
        self._icon.show()

        self._thumb = Thumb()
        self._thumb.set_size_request(preview.THUMB_WIDTH, preview.THUMB_HEIGHT)
        self._thumb.show()

        self._thumb_box = gtk.HBox()
        main.pack_start(self._thumb_box, expand=False)

        self._title = Title(max_line_count=2)
        main.pack_start(self._title, expand=False)

        self._date = Timestamp(wrap=True, xalign=0.0)
        self._date.set_size_request(preview.THUMB_WIDTH, -1)
        main.pack_start(self._date, expand=False)

        self.show_all()

    def do_fill_in_cell_content(self, table, offset, metadata):
        self._keep.fill_in(metadata)
        self._details.fill_in(metadata)
        self._title.fill_in(metadata)
        self._date.fill_in(metadata)
        self._icon.fill_in(metadata)
        self._thumb.fill_in(metadata)

        if self._last_thumb_offset != offset or \
                self._last_thumb_uid != metadata.get('uid') or \
                self._last_thumb_mtime != metadata.get('timestamp'):
            self._set_thumb_widget(self._icon)
            self._last_thumb_offset = None
            self._last_thumb_uid = metadata.get('uid')
            self._last_thumb_mtime = metadata.get('timestamp')
            preview.fetch(offset, metadata)
        else:
            self._set_thumb_widget(self._thumb)

    def fill_pixbuf_in(self, offset, pixbuf):
        self._last_thumb_offset = offset
        self._thumb.set_from_pixbuf(pixbuf)
        self._set_thumb_widget(self._thumb)

    def _set_thumb_widget(self, widget):
        if widget not in self._thumb_box.get_children():
            for child in self._thumb_box.get_children():
                self._thumb_box.remove(child)
            self._thumb_box.pack_start(widget, expand=False)


class ThumbsView(HomogeneView):

    def __init__(self):
        HomogeneView.__init__(self, _Cell)

        cell_width = style.DEFAULT_PADDING * 2 + \
                     style.GRID_CELL_SIZE + \
                     preview.THUMB_WIDTH

        cell_height = style.DEFAULT_PADDING * 2 + \
                      preview.THUMB_HEIGHT + \
                      style.DEFAULT_PADDING * 2 + \
                      entry.TEXT_HEIGHT * 4

        self.cell_size = (cell_width, cell_height)

        self.connect('frame-scrolled', self.__frame_scrolled_cb)
        preview.fetched.connect(self.__preview_fetched_cb)

    def __frame_scrolled_cb(self, table):
        preview.discard_queue(table.frame_range)

    def __preview_fetched_cb(self, sender, signal, offset, pixbuf):
        cell = self.get_cell(offset)
        if cell is not None:
            cell.fill_pixbuf_in(offset, pixbuf)
            self.refill([offset])
