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

from jarabe.journal.sugarbin import SugarBin


# Having spare rows let us making smooth scrolling w/o empty spaces
_SPARE_ROWS_COUNT = 2


class HomogeneTable(SugarBin):
    """
    Grid widget with homogeneously placed children of the same class.

    Grid has fixed number of columns that are visible all time and unlimited
    rows number. There are frame cells - visible at particular moment - frame
    cells and virtual (widget is model less itself and only ask callback
    object about right cell's value) ones - just cells. User can scroll up/down
    grid to see all virtual cells and the same frame cell could represent
    content of various virtual cells (widget will call do_fill_cell_in to
    refill frame cell content) in different time moments.

    By default widget doesn't have any cells, to make it useful, assign proper
    value to either frame_size or cell_size property. Also set cell_count to
    set number of virual rows.

    """
    __gsignals__ = {
            'set-scroll-adjustments': (gobject.SIGNAL_RUN_FIRST, None,
                                      [gtk.Adjustment, gtk.Adjustment]),
            'cursor-changed': (gobject.SIGNAL_RUN_FIRST, None, []),
            'frame-scrolled': (gobject.SIGNAL_RUN_FIRST, None, []),
            }

    def __init__(self, **kwargs):
        self._row_cache = []
        self._cell_cache = []
        self._cell_cache_pos = 0
        self._adjustments = []
        self._bin_window = None
        self._cell_count = 0
        self._cell_length = 0
        self._frame_size = [None, None]
        self._cell_size = [None, None]
        self._cursor_index = None
        self._pending_allocate = None
        self._frame_range = None
        self._orientation = gtk.ORIENTATION_VERTICAL
        self._hover_selection = False
        self._cursor_visible = True

        SugarBin.__init__(self, **kwargs)

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
        self._setup_adjustment(dry_run=False)
        self._resize_table()

    """Number of virtual cells
       Defines maximal number of virtual rows, the minimal has being described
       by frame_size/cell_size values."""
    cell_count = gobject.property(getter=get_cell_count, setter=set_cell_count)

    def get_orientation(self):
        return self._orientation

    def set_orientation(self, value):
        if self._orientation == value:
            return

        self._orientation = value
        for adjustment, __ in self._adjustments:
            adjustment.lower = 0
            adjustment.upper = 0
        self._resize_table()

    orientation = gobject.property(getter=get_orientation,
            setter=set_orientation)

    def get_hover_selection(self):
        return self._hover_selection

    def set_hover_selection(self, value):
        if value == self.hover_selection:
            return
        if value:
            self.add_events(gtk.gdk.POINTER_MOTION_HINT_MASK | \
                            gtk.gdk.POINTER_MOTION_MASK)
        self._hover_selection = value

    def do_motion_notify_event(self, event):
        if not self.hover_selection:
            return
        self.cursor = self.get_cell_at_pos(*self.get_pointer())

    hover_selection = gobject.property(
            getter=get_hover_selection, setter=set_hover_selection)

    def get_cell(self, cell_index):
        """Get cell widget by index
           Method returns non-None values only for visible cells."""
        cell = self._get_cell(cell_index)
        if cell is None:
            return None
        else:
            return cell.widget

    def get_cursor(self):
        return self._cursor_index

    def set_cursor(self, cell_index):
        cell_index = min(max(0, cell_index), self.cell_count - 1)
        if cell_index == self.cursor:
            return
        self.scroll_to_cell(cell_index)
        self._set_cursor(cell_index)

    """Selected cell"""
    cursor = gobject.property(getter=get_cursor, setter=set_cursor)

    def get_cursor_visible(self):
        return self._cursor_visible

    def set_cursor_visible(self, value):
        if value == self.cursor_visible:
            return
        cell = self._get_cell(self.cursor)
        if cell is not None:
            self.do_highlight_cell(cell.widget, value)
        self._cursor_visible = value

    cursor_visible = gobject.property(
            getter=get_cursor_visible, setter=set_cursor_visible)

    def get_frame_range(self):
        if self._frame_range is None:
            return xrange(0)
        else:
            begin, end = self._frame_range
            return xrange(begin, end + 1)

    """Range of visible cells"""
    frame_range = gobject.property(getter=get_frame_range)

    @property
    def frame_cells(self):
        for cell in self._cell_cache:
            yield cell.widget

    def get_focus_cell(self):
        if self.cursor is None or self.props.has_focus:
            return False
        cell = self._get_cell(self.cursor)
        if cell is None:
            return False
        else:
            # XXX why gtk.Container.get_focus_child() doesn't work some time
            window = self.get_toplevel()
            if window is None:
                return False
            focus = window.get_focus()
            while focus is not None and focus.parent is not None:
                if focus is self:
                    return True
                focus = focus.parent
            return False

    def set_focus_cell(self, value):
        if value == self.focus_cell:
            return
        if value:
            if not self.props.has_focus:
                self.grab_focus()
            cell = self._get_cell(self.cursor)
            if cell is not None:
                cell.widget.child_focus(gtk.DIR_TAB_FORWARD)
        else:
            self.grab_focus()

    """Selected cell got focused"""
    focus_cell = gobject.property(getter=get_focus_cell, setter=set_focus_cell)

    def get_cell_at_pos(self, x, y):
        """Get cell index at pos which is relative to HomogeneTable widget"""
        if self._empty:
            return None

        x = min(max(0, x), self.width - 1)
        y = min(max(0, y), self.height - 1)

        x, y = self._rotate(x, y)
        y += self._pos

        return self._get_cell_at_pos(x, y)

    def scroll_to_cell(self, cell_index):
        """Scroll HomogeneTable to position where cell is viewable"""
        if self._empty or cell_index == self.cursor:
            return

        self.focus_cell = False

        row = cell_index / self._column_count
        pos = row * self._cell_length

        if pos <= self._pos:
            self._pos = pos
        else:
            pos = pos + self._cell_length - self._frame_length
            if pos >= self._pos:
                self._pos = pos

    def refill(self, cells=None):
        """Force HomogeneTable widget to run filling method for all cells"""
        for cell in self._cell_cache:
            if cells is None or cell.index in cells:
                cell.index = -1
        self._allocate_rows(force=False)

    def do_cell_new(self):
        raise Exception('do_cell_new() should be implemented in subclass')

    def do_fill_cell_in(self, cell, cell_index):
        cell.do_fill_in(self, cell_index)

    def do_highlight_cell(self, cell, selected):
        pass

    # gtk.Widget overrides

    def do_scroll_event(self, event):
        if self._adjustment is not None and \
                self.orientation == gtk.ORIENTATION_HORIZONTAL:
            adj = self._adjustment
            if event.direction == gtk.gdk.SCROLL_UP:
                value = max(0, adj.value - self._cell_length)
            elif event.direction == gtk.gdk.SCROLL_DOWN:
                value = min(self._max_pos, adj.value + self._cell_length)
            else:
                return False
            adj.value = value
            return True
        return False

    def do_realize(self):
        SugarBin.do_realize(self)

        self._bin_window = gtk.gdk.Window(
                self.window,
                window_type=gtk.gdk.WINDOW_CHILD,
                x=self._rotate(self.x, -self._pos)[0],
                y=self._rotate(-self._pos, self.y)[0],
                width=self._rotate(self._thickness, self._length)[0],
                height=self._rotate(self._length, self._thickness)[0],
                colormap=self.get_colormap(),
                wclass=gtk.gdk.INPUT_OUTPUT,
                event_mask=(self.get_events() | gtk.gdk.EXPOSURE_MASK |
                            gtk.gdk.SCROLL_MASK))
        self._bin_window.set_user_data(self)
        self.style.set_background(self._bin_window, gtk.STATE_NORMAL)

        for row in self._row_cache:
            for cell in row:
                cell.widget.set_parent_window(self._bin_window)

        if self._pending_allocate is not None:
            self._allocate_rows(force=self._pending_allocate)
            self._pending_allocate = None

    def do_size_allocate(self, allocation):
        resize_tabel = tuple(self.allocation) != tuple(allocation)
        SugarBin.do_size_allocate(self, allocation)
        if resize_tabel:
            self._resize_table()

    def do_unrealize(self):
        self._bin_window.set_user_data(None)
        self._bin_window.destroy()
        self._bin_window = None
        SugarBin.do_unrealize(self)

    def do_style_set(self, style):
        SugarBin.do_style_set(self, style)
        if self.flags() & gtk.REALIZED:
            self.style.set_background(self._bin_window, gtk.STATE_NORMAL)

    def do_expose_event(self, event):
        if event.window == self._bin_window:
            SugarBin.do_expose_event(self, event)
        return False

    def do_map(self):
        SugarBin.do_map(self)

        for row in self._row_cache:
            for cell in row:
                if cell.widget.props.visible:
                    cell.widget.map()

        self._bin_window.show()

    def do_size_request(self, req):
        req.width = 0
        req.height = 0

        for row in self._row_cache:
            for cell in row:
                cell.widget.size_request()

    def do_set_scroll_adjustments(self, hadjustment, vadjustment):
        for adjustment, handler in self._adjustments:
            adjustment.disconnect(handler)

        if vadjustment is None or hadjustment is None:
            self._adjustments = []
            return

        self._adjustments = (
                [vadjustment, vadjustment.connect('value-changed',
                    self.__adjustment_value_changed_cb)],
                [hadjustment, hadjustment.connect('value-changed',
                    self.__adjustment_value_changed_cb)])

        self._setup_adjustment(dry_run=True)

    # gtk.Container overrides

    def do_forall(self, include_internals, callback, data):
        for row in self._row_cache:
            for cell in row:
                #if cell.widget.has_screen():
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
            cursor = self._get_cell_at_pos(*self._rotate(x, y))
            if self.cursor is None or cursor not in self.frame_range:
                self.cursor = cursor

    def do_focus(self, type):
        if self.focus_cell:
            cell = self._get_cell(self.cursor)
            if cell is None:
                logging.error('cannot find cursor cell')
            elif not cell.widget.child_focus(type):
                self.grab_focus()
            return True
        else:
            if self.props.has_focus:
                return False
            else:
                if self.cursor is None:
                    x, y = self.get_pointer()
                    self._set_cursor(self.get_cell_at_pos(x, y))
                self.grab_focus()
                return True

    @property
    def _empty(self):
        return not self._row_cache

    @property
    def _adjustment(self):
        if not self._adjustments:
            return None
        else:
            return self._rotate(*[i[0] for i in self._adjustments])[0]

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
    def _pos(self):
        if self._adjustment is None or math.isnan(self._adjustment.value):
            return 0
        else:
            return max(0, int(self._adjustment.value))

    @_pos.setter
    def _pos(self, value):
        if self._adjustment is not None:
            self._adjustment.value = value

    @property
    def _max_pos(self):
        if self._adjustment is None:
            return 0
        else:
            return max(0, self._length - self._frame_length)

    @property
    def _thickness(self):
        return self._rotate(self.width, self.height)[0]

    @property
    def _frame_length(self):
        return self._rotate(self.height, self.width)[0]

    @property
    def _length(self):
        if self._adjustment is None:
            return self._frame_length
        else:
            return int(self._adjustment.upper)

    def _rotate(self, x, y):
        if self._orientation == gtk.ORIENTATION_VERTICAL:
            return (x, y)
        else:
            return (y, x)

    def _get_cell(self, cell_index):
        if cell_index is None:
            return None
        column = cell_index % self._column_count
        base_index = cell_index - column
        for row in self._row_cache:
            if row[0].is_valid() and row[0].index == base_index:
                return row[column]
        return None

    def _get_row_pos(self, row):
        allocation = row[0].widget.allocation
        return self._rotate(allocation.y, allocation.x)[0]

    def _set_cursor(self, cell_index):
        if self.cursor_visible:
            cell = self._get_cell(self.cursor)
            if cell is not None:
                self.do_highlight_cell(cell.widget, False)

        self._cursor_index = cell_index

        if self.cursor_visible:
            cell = self._get_cell(self.cursor)
            if cell is not None:
                self.do_highlight_cell(cell.widget, True)

        self.emit('cursor-changed')

    def _get_cell_at_pos(self, x, y):
        cell_row = y / self._cell_length
        cell_column = x / (self._thickness / self._column_count)
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
            cell.widget = self.do_cell_new()
            assert(cell.widget is not None)
            self._cell_cache.append(cell)
            self._cell_cache_pos = len(self._cell_cache)

        cell.invalidate_pos()
        return cell

    def _resize_table(self):
        x, y, w, h = self.allocation
        if x + w <= 0 or y + h <= 0:
            return

        row_count, column_count = self._frame_size
        cell_width, cell_height = self._cell_size

        if row_count is None:
            if cell_height is None:
                return
            row_count = math.ceil(self._frame_length / float(cell_height))
            row_count = max(1, int(row_count))
            self._cell_length = cell_height
        else:
            self._cell_length = self._frame_length / self._frame_row_count

        if column_count is None:
            if cell_width is None:
                return
            column_count = max(1, self._thickness / cell_width)

        if (column_count != self._column_count or \
                row_count != self._frame_row_count):
            self._abandon_cells()
            for i_ in range(row_count + _SPARE_ROWS_COUNT):
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
                    cell.index = -1

        self._setup_adjustment(dry_run=True)

        if self.flags() & gtk.REALIZED:
            self._bin_window.resize(
                    *self._rotate(self._thickness, self._length))

        self._allocate_rows(force=True)

    def _setup_adjustment(self, dry_run):
        if self._adjustment is None:
            return

        self._adjustment.lower = 0
        self._adjustment.upper = self._row_count * self._cell_length
        self._adjustment.page_size = self._frame_length
        self._adjustment.changed()

        if self._pos > self._max_pos:
            self._pos = self._max_pos
            if not dry_run:
                self._adjustment.value_changed()

    def _allocate_cells(self, row, cell_y):
        cell_x = 0
        cell_row = cell_y / self._cell_length
        cell_index = cell_row * self._column_count

        for cell_column, cell in enumerate(row):
            if cell.index != cell_index:
                if cell_index < self.cell_count:
                    self.do_fill_cell_in(cell.widget, cell_index)
                    if self.cursor_visible:
                        self.do_highlight_cell(cell.widget,
                                cell_index == self.cursor)
                    cell.widget.show()
                else:
                    cell.widget.hide()
                cell.index = cell_index

            cell_thickness = self._thickness / self._column_count

            alloc = gtk.gdk.Rectangle()
            alloc.x, alloc.y = self._rotate(cell_x, cell_y)
            alloc.width, alloc.height = \
                    self._rotate(cell_thickness, self._cell_length)

            cell.widget.size_request()
            cell.widget.size_allocate(alloc)

            cell_x += cell_thickness
            cell_index += 1

    def _allocate_rows(self, force):
        if self._empty:
            return

        if not self.flags() & gtk.REALIZED:
            self._pending_allocate = self._pending_allocate or force
            return

        pos = self._pos
        if pos < 0 or pos > self._max_pos:
            return

        spare_rows = []
        visible_rows = []
        frame_rows = []
        page_end = pos + self._frame_length

        if force:
            spare_rows = [] + self._row_cache
        else:
            for row in self._row_cache:
                row_pos = self._get_row_pos(row)
                if row_pos < 0 or row_pos > page_end or \
                        (row_pos + self._cell_length) < pos:
                    spare_rows.append(row)
                else:
                    bisect.insort_right(visible_rows,
                            _IndexedRow(row, row_pos))

        if visible_rows or spare_rows:

            def try_insert_spare_row(pos_begin, pos_end):
                while pos_begin < pos_end:
                    if not spare_rows:
                        logging.error('spare_rows should not be empty')
                        return
                    row = spare_rows.pop()
                    self._allocate_cells(row, pos_begin)
                    pos_begin = pos_begin + self._cell_length
                    frame_rows.append(row)

            # visible_rows could not be continuous
            # lets try to add spare rows to missed points
            next_row_pos = int(pos) - int(pos) % self._cell_length
            for i in visible_rows:
                row_pos = self._get_row_pos(i.row)
                try_insert_spare_row(next_row_pos, row_pos)
                self._allocate_cells(i.row, row_pos)
                next_row_pos = row_pos + self._cell_length
                frame_rows.append(i.row)

            try_insert_spare_row(next_row_pos, page_end)

        self._bin_window.move(*self._rotate(self.x, self.y + int(-pos)))
        self._bin_window.process_updates(True)

        if frame_rows:
            frame_range = (frame_rows[0][0].index, frame_rows[-1][-1].index)
        else:
            frame_range = None
        if frame_range != self._frame_range:
            self._frame_range = frame_range
            self.emit('frame-scrolled')

        if self.focus_cell and self.cursor not in self.frame_range:
            self.focus_cell = False

    def __adjustment_value_changed_cb(self, adjustment):
        self._allocate_rows(force=False)
        if self.hover_selection:
            self.cursor = self.get_cell_at_pos(*self.get_pointer())

    def __key_press_event_cb(self, widget, event):
        if self._empty or self.cursor is None:
            return

        page = self._column_count * self._frame_row_count

        prev_cell, prev_row = self._rotate(gtk.keysyms.Left, gtk.keysyms.Up)
        next_cell, next_row = self._rotate(gtk.keysyms.Right, gtk.keysyms.Down)

        if event.keyval == gtk.keysyms.Escape and self.focus_cell:
            self.focus_cell = False
        elif event.keyval == gtk.keysyms.Return:
            self.focus_cell = not self.focus_cell
        elif event.keyval == prev_cell:
            self.cursor -= 1
        elif event.keyval == next_cell:
            self.cursor += 1
        elif event.keyval == prev_row:
            if self.cursor >= self._column_count:
                self.cursor -= self._column_count
        elif event.keyval == next_row:
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

    def __init__(self, row, row_pos):
        self.row = row
        self.row_pos = row_pos

    def __lt__(self, other):
        return self.row_pos < other.row_pos


class _Cell:
    widget = None
    index = -1

    def invalidate_pos(self):
        self.widget.size_allocate(gtk.gdk.Rectangle(-1, -1, 0, 0))

    def is_valid(self):
        return self.index >= 0 and self.widget is not None and \
               self.widget.allocation >= 0 and self.widget.allocation >= 0


HomogeneTable.set_set_scroll_adjustments_signal('set-scroll-adjustments')
