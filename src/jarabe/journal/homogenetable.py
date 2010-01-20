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
import math
import bisect
import logging

# Having spare rows let us making smooth scrolling w/o empty spaces
_SPARE_ROWS_COUNT = 2


class VHomogeneTable(gtk.Container):
    """
    Grid widget with homogeneously placed children of the same class.

    Grid has fixed number of columns that are visible all time and unlimited
    rows number. There are frame cells - visible at particular moment - frame
    cells and virtual (widget is model less itself and only ask callback
    object about right cell's value) ones - just cells. User can scroll up/down
    grid to see all virtual cells and the same frame cell could represent
    content of various virtual cells (widget will call cell_fill_in_cb callback
    to refill frame cell content) in different time moments.

    By default widget doesn't have any cells, to make it useful, assign proper
    value to either frame_size or cell_size property. Also set cell_count to
    set number of virual rows.

    """
    __gsignals__ = {
            'set-scroll-adjustments': (gobject.SIGNAL_RUN_FIRST, None,
                                      [gtk.Adjustment, gtk.Adjustment]),
            'cursor-changed': (gobject.SIGNAL_RUN_FIRST, None, [object]),
            }

    def __init__(self, cell_class, **kwargs):
        assert(hasattr(cell_class, 'do_fill_in'))

        self._cell_class = cell_class
        self._row_cache = []
        self._cell_cache = []
        self._cell_cache_pos = 0
        self._adjustment = None
        self._adjustment_value_changed_id = None
        self._bin_window = None
        self._cell_count = 0
        self._cell_height = 0
        self._frame_size = [None, None]
        self._cell_size = [None, None]
        self._selected_index = None
        self._editable = True
        self._pending_allocate = None

        gtk.Container.__init__(self, **kwargs)

        # when focused cell is out of visible frame,
        # table itslef will be focused to follow gtk focusing scheme
        self.props.can_focus = True

        self.connect('key-press-event', self.__key_press_event_cb)

    def set_frame_size(self, value):
        value = list(value)
        if self._frame_size == value:
            return

        if value[0] is not None:
            self._cell_size[1] = None
        if value[1] is not None:
            self._cell_size[0] = None

        self._frame_size = value
        self._resize_table()

    """Set persistent number of frame rows/columns, value is (rows, columns)
       Cells will be resized while resizing widget.
       Mutually exclusive to cell_size."""
    frame_size = gobject.property(setter=set_frame_size)

    def set_cell_size(self, value):
        value = list(value)
        if self._cell_size == value:
            return

        if value[0] is not None:
            self._frame_size[1] = None
        if value[1] is not None:
            self._frame_size[0] = None

        self._cell_size = value
        self._resize_table()

    """Set persistent cell sizes, value is (width, height)
       Number of cells will be changed while resizing widget.
       Mutually exclusive to frame_size."""
    cell_size = gobject.property(setter=set_cell_size)

    def get_cell_count(self):
        return self._cell_count

    def set_cell_count(self, count):
        if self._cell_count == count:
            return
        self._cell_count = count
        self.refill()
        self._setup_adjustment(dry_run=False)

    """Number of virtual cells
       Defines maximal number of virtual rows, the minimal has being described
       by frame_size/cell_size values."""
    cell_count = gobject.property(getter=get_cell_count, setter=set_cell_count)

    def get_cell(self, cell_index):
        """Get cell widget by index
           Method returns non-None values only for visible cells."""
        cell = self._get_cell(cell_index)
        if cell is None:
            return None
        else:
            return cell.widget

    def __getitem__(self, cell_index):
        return self.get_cell(cell_index)

    def get_cursor(self):
        return self._selected_index

    def set_cursor(self, cell_index):
        cell_index = min(max(0, cell_index), self.cell_count - 1)
        if cell_index == self.cursor:
            return
        self.scroll_to_cell(cell_index)
        self._set_cursor(cell_index)

    """Selected cell"""
    cursor = gobject.property(getter=get_cursor, setter=set_cursor)

    def get_editable(self):
        return self._editable

    def set_editable(self, value):
        self._editable = value

    """Can cells be focused"""
    editable = gobject.property(getter=get_editable, setter=set_editable)

    def get_editing(self):
        if not self._editable or self._selected_index is None or \
                self.props.has_focus:
            return False
        cell = self._get_cell(self._selected_index)
        if cell is None:
            return False
        else:
            return cell.widget.get_focus_child()

    def set_editing(self, value):
        if value == self.editing:
            return
        if value:
            if not self.props.has_focus:
                self.grab_focus()
            cell = self._get_cell(self._selected_index)
            if cell is not None:
                cell.widget.child_focus(gtk.DIR_TAB_FORWARD)
        else:
            self.grab_focus()

    """Selected cell got focused"""
    editing = gobject.property(getter=get_editing, setter=set_editing)

    def get_cell_at_pos(self, x, y):
        """Get cell index at pos which is relative to VHomogeneTable widget"""
        if self._empty:
            return None

        x, y = self.get_pointer()
        x = min(max(0, x), self.allocation.width)
        y = min(max(0, y), self.allocation.height) + self._pos_y

        return self._get_cell_at_pos(x, y)

    def scroll_to_cell(self, cell_index):
        """Scroll VHomogeneTable to position where cell is viewable"""
        if self._empty:
            return

        self.editing = False

        row = cell_index / self._column_count
        pos = row * self._cell_height

        if pos < self._pos_y:
            self._pos_y = pos
        elif pos + self._cell_height >= self._pos_y + self._page:
            self._pos_y = pos + self._cell_height - self._page
        else:
            return

        self._pos_changed()

    def refill(self):
        """Force VHomogeneTable widget to run filling method for all cells"""
        for cell in self._cell_cache:
            cell.invalidate_pos()
            cell.index = -1
        self._allocate_rows(force=True)

    # gtk.Widget overrides

    def do_realize(self):
        self.set_flags(gtk.REALIZED)

        self.window = gtk.gdk.Window(
                self.get_parent_window(),
                window_type=gtk.gdk.WINDOW_CHILD,
                x=self.allocation.x,
                y=self.allocation.y,
                width=self.allocation.width,
                height=self.allocation.height,
                wclass=gtk.gdk.INPUT_OUTPUT,
                colormap=self.get_colormap(),
                event_mask=gtk.gdk.VISIBILITY_NOTIFY_MASK)
        self.window.set_user_data(self)

        self._bin_window = gtk.gdk.Window(
                self.window,
                window_type=gtk.gdk.WINDOW_CHILD,
                x=0,
                y=-self._pos_y,
                width=self.allocation.width,
                height=self._max_y,
                colormap=self.get_colormap(),
                wclass=gtk.gdk.INPUT_OUTPUT,
                event_mask=(self.get_events() | gtk.gdk.EXPOSURE_MASK |
                            gtk.gdk.SCROLL_MASK))
        self._bin_window.set_user_data(self)

        self.set_style(self.style.attach(self.window))
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.style.set_background(self._bin_window, gtk.STATE_NORMAL)

        for row in self._row_cache:
            for cell in row:
                cell.widget.set_parent_window(self._bin_window)

        if self._pending_allocate is not None:
            self._allocate_rows(force=self._pending_allocate)
            self._pending_allocate = None
        #self.queue_resize()

    def do_size_allocate(self, allocation):
        resize_tabel = self.allocation != allocation
        self.allocation = allocation

        if resize_tabel:
            self._resize_table()

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)

    def do_unrealize(self):
        self._bin_window.set_user_data(None)
        self._bin_window.destroy()
        self._bin_window = None
        gtk.Container.do_unrealize(self)

    def do_style_set(self, style):
        gtk.Widget.do_style_set(self, style)
        if self.flags() & gtk.REALIZED:
            self.style.set_background(self._bin_window, gtk.STATE_NORMAL)

    def do_expose_event(self, event):
        if event.window != self._bin_window:
            return False
        gtk.Container.do_expose_event(self, event)
        return False

    def do_map(self):
        self.set_flags(gtk.MAPPED)

        for row in self._row_cache:
            for cell in row:
                cell.widget.map()

        self._bin_window.show()
        self.window.show()

    def do_size_request(self, req):
        req.width = 0
        req.height = 0

        for row in self._row_cache:
            for cell in row:
                cell.widget.size_request()

    def do_set_scroll_adjustments(self, hadjustment, vadjustment):
        if vadjustment is None or vadjustment == self._adjustment:
            return

        if self._adjustment is not None:
            self._adjustment.disconnect(self._adjustment_value_changed_id)

        self._adjustment = vadjustment
        self._setup_adjustment(dry_run=True)

        self._adjustment_value_changed_id = vadjustment.connect(
                'value-changed', self.__adjustment_value_changed_cb)

    # gtk.Container overrides

    def do_forall(self, include_internals, callback, data):
        for row in self._row_cache:
            for cell in row:
                callback(cell.widget, data)

    def do_add(self, widget):
        # container is not intended to add children manually
        assert(False)

    def do_remove(self, widget):
        # container is not intended to remove children manually
        pass

    def do_set_focus_child(self, widget):
        if widget is not None:
            x, y, __, __ = widget.allocation
            self.cursor = self._get_cell_at_pos(x, y)

    def do_focus(self, type):
        if self.editing:
            cell = self._get_cell(self._selected_index)
            if cell is None:
                logging.error('cannot find _selected_index cell')
            elif not cell.widget.child_focus(type):
                self.grab_focus()
            return True
        else:
            if self.props.has_focus:
                return False
            else:
                if self._selected_index is None:
                    x, y = self.get_pointer()
                    self._set_cursor(self.get_cell_at_pos(x, y))
                self.grab_focus()
                return True

    @property
    def _frame_range(self):
        if self._empty:
            return xrange(0)
        else:
            first = self._pos_y / self._cell_height * self._column_count
            last = int(math.ceil(float(self._pos_y + self._page) / \
                    self._cell_height) * self._column_count)
            return xrange(first, min(last, self.cell_count))

    @property
    def _empty(self):
        return not self._row_cache

    @property
    def _column_count(self):
        if self._row_cache:
            return len(self._row_cache[0])
        else:
            return 0

    @property
    def _row_count(self):
        if self._column_count == 0:
            return 0
        else:
            rows = math.ceil(float(self.cell_count) / self._column_count)
            return max(self._frame_row_count, rows)

    @property
    def _frame_row_count(self):
        return len(self._row_cache) - _SPARE_ROWS_COUNT

    @property
    def _page(self):
        return self._frame_row_count * self._cell_height

    @property
    def _pos_y(self):
        if self._adjustment is None or math.isnan(self._adjustment.value):
            return 0
        else:
            return max(0, int(self._adjustment.value))

    @_pos_y.setter
    def _pos_y(self, value):
        if self._adjustment is not None:
            self._adjustment.value = value

    @property
    def _max_pos_y(self):
        if self._adjustment is None:
            return 0
        else:
            return max(0, self._max_y - self._page)

    @property
    def _max_y(self):
        if self._adjustment is None:
            return self.allocation.height
        else:
            return int(self._adjustment.upper)

    def _get_cell(self, cell_index):
        if cell_index is None:
            return None
        column = cell_index % self._column_count
        base_index = cell_index - column
        for row in self._row_cache:
            if row[0].is_valid() and row[0].index == base_index:
                return row[column]
        return None

    def _set_cursor(self, cell_index):
        old_cursor = self._selected_index
        self._selected_index = cell_index
        if old_cursor != self._selected_index:
            self.emit('cursor-changed', old_cursor)

    def _get_cell_at_pos(self, x, y):
        cell_row = y / self._cell_height
        cell_column = x / (self.allocation.width / self._column_count)
        cell_index = cell_row * self._column_count + cell_column
        return min(cell_index, self.cell_count - 1)

    def _pos_changed(self):
        if self._adjustment is not None:
            self._adjustment.value_changed()

    def _abandon_cells(self):
        for row in self._row_cache:
            for cell in row:
                cell.widget.unparent()
        self._cell_cache_pos = 0
        self._row_cache = []

    def _pop_a_cell(self):
        if self._cell_cache_pos < len(self._cell_cache):
            cell = self._cell_cache[self._cell_cache_pos]
            self._cell_cache_pos += 1
        else:
            cell = _Cell()
            cell.widget = self._cell_class()
            self._cell_cache.append(cell)
            self._cell_cache_pos = len(self._cell_cache)

        cell.invalidate_pos()
        return cell

    def _resize_table(self):
        x, y, width, height = self.allocation
        if x < 0 or y < 0:
            return

        frame_row_count, column_count = self._frame_size
        cell_width, cell_height = self._cell_size

        if frame_row_count is None:
            if cell_height is None:
                return
            frame_row_count = max(1, height / cell_height)
        if column_count is None:
            if cell_width is None:
                return
            column_count = max(1, width / cell_width)

        if (column_count != self._column_count or \
                frame_row_count != self._frame_row_count):
            self._abandon_cells()
            for i_ in range(frame_row_count + _SPARE_ROWS_COUNT):
                row = []
                for j_ in range(column_count):
                    cell = self._pop_a_cell()
                    if self.flags() & gtk.REALIZED:
                        cell.widget.set_parent_window(self._bin_window)
                    cell.widget.set_parent(self)
                    row.append(cell)
                self._row_cache.append(row)
        else:
            for row in self._row_cache:
                for cell in row:
                    cell.invalidate_pos()

        self._cell_height = height / self._frame_row_count
        self._setup_adjustment(dry_run=True)

        if self.flags() & gtk.REALIZED:
            self._bin_window.resize(self.allocation.width, self._max_y)

        self._allocate_rows(force=True)

    def _setup_adjustment(self, dry_run):
        if self._adjustment is None:
            return

        self._adjustment.lower = 0
        self._adjustment.upper = self._row_count * self._cell_height
        self._adjustment.page_size = self._page
        self._adjustment.changed()

        if self._pos_y > self._max_pos_y:
            self._pos_y = self._max_pos_y
            if not dry_run:
                self._adjustment.value_changed()

    def _allocate_cells(self, row, cell_y):
        cell_x = 0
        cell_row = cell_y / self._cell_height
        cell_index = cell_row * self._column_count

        for cell_column, cell in enumerate(row):
            if cell.index != cell_index:
                if cell_index < self.cell_count:
                    cell.widget.do_fill_in(self, cell_index)
                    cell.widget.show()
                else:
                    cell.widget.hide()
                cell.index = cell_index

            cell_alloc = gtk.gdk.Rectangle(cell_x, cell_y)
            cell_alloc.width = self.allocation.width / self._column_count
            cell_alloc.height = self._cell_height
            cell.widget.size_request()
            cell.widget.size_allocate(cell_alloc)

            cell_x += cell_alloc.width
            cell_index += 1

    def _allocate_rows(self, force):
        if self._empty:
            return

        if not self.flags() & gtk.REALIZED:
            self._pending_allocate = self._pending_allocate or force
            return

        pos = self._pos_y
        if pos < 0 or pos > self._max_pos_y:
            return

        spare_rows = []
        visible_rows = []
        page_end = pos + self._page

        if force:
            spare_rows = [] + self._row_cache
        else:
            for row in self._row_cache:
                row_y = row[0].widget.allocation.y
                if row_y < 0 or row_y > page_end or \
                        (row_y + self._cell_height) < pos:
                    spare_rows.append(row)
                else:
                    bisect.insort_right(visible_rows, _IndexedRow(row))

        if visible_rows or spare_rows:

            def try_insert_spare_row(cell_y, end_y):
                while cell_y < end_y:
                    if not spare_rows:
                        logging.error('spare_rows should not be empty')
                        return
                    row = spare_rows.pop()
                    self._allocate_cells(row, cell_y)
                    cell_y = cell_y + self._cell_height

            # visible_rows could not be continuous
            # lets try to add spare rows to missed points
            cell_y = int(pos) - int(pos) % self._cell_height
            for i in visible_rows:
                cell = i.row[0].widget.allocation
                try_insert_spare_row(cell_y, cell.y)
                cell_y = cell.y + cell.height

            try_insert_spare_row(cell_y, page_end)

            if self.editing and self._selected_index not in self._frame_range:
                self.editing = False

        self._bin_window.move(0, int(-pos))
        self._bin_window.process_updates(True)

    def __adjustment_value_changed_cb(self, adjustment):
        self._allocate_rows(force=False)

    def __key_press_event_cb(self, widget, event):
        if self._empty or self.cursor is None:
            return

        page = self._column_count * self._frame_row_count

        if event.keyval == gtk.keysyms.Return and self.editable:
            self.editing = not self.editing
        elif event.keyval == gtk.keysyms.Left:
            self.cursor -= 1
        elif event.keyval == gtk.keysyms.Right:
            self.cursor += 1
        elif event.keyval == gtk.keysyms.Up:
            if self.cursor >= self._column_count:
                self.cursor -= self._column_count
        elif event.keyval == gtk.keysyms.Down:
            if self.cursor / self._column_count < \
                    (self.cell_count - 1) / self._column_count:
                self.cursor += self._column_count
        elif event.keyval in (gtk.keysyms.Page_Up, gtk.keysyms.KP_Page_Up):
            self.cursor -= page
        elif event.keyval in (gtk.keysyms.Page_Down, gtk.keysyms.KP_Page_Down):
            self.cursor += page
        elif event.keyval in (gtk.keysyms.Home, gtk.keysyms.KP_Home):
            self.cursor = 0
        elif event.keyval in (gtk.keysyms.End, gtk.keysyms.KP_End):
            self.cursor = self.cell_count - 1
        else:
            return False

        return True


class _IndexedRow:

    def __init__(self, row):
        self.row = row

    def __lt__(self, other):
        return self.row[0].widget.allocation.y < \
               other.row[0].widget.allocation.y


class _Cell:
    widget = None
    index = -1

    def invalidate_pos(self):
        self.widget.size_allocate(gtk.gdk.Rectangle(-1, -1, 0, 0))

    def is_valid(self):
        return self.index >= 0 and self.widget is not None and \
               self.widget.allocation >= 0 and self.widget.allocation >= 0


VHomogeneTable.set_set_scroll_adjustments_signal('set-scroll-adjustments')
