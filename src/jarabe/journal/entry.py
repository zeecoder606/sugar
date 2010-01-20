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

import logging

import gtk
import gobject
import pango


class Entry(gtk.TextView):
    """One paragraph string entry with additional features

       * multi line mode for wrapping long lines
       * having wrapping and ellipses simultaneously in inactive mode
       * accent in inactive mode

       NOTE: Use text property instead of buffer, buffer's value will be
             changed in inactive mode

    """

    def __init__(self, **kwargs):
        self._max_line_count = 1
        self._text = None

        gobject.GObject.__init__(self, **kwargs)

        self._tag = self.props.buffer.create_tag()
        self._tag.props.weight = pango.WEIGHT_BOLD

        gtk.TextView.set_accepts_tab(self, False)
        self.set_max_line_count(self._max_line_count)

        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('focus-in-event', self.__focus_in_event_cb)
        self.connect('focus-out-event', self.__focus_out_event_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

    def set_accepts_tab(self, value):
        # accepts_tab cannot be set by users
        assert(False)

    def get_accepts_tab(self):
        return gtk.TextView.get_accepts_tab()

    accepts_tab = gobject.property(
            getter=get_accepts_tab, setter=set_accepts_tab)

    def set_wrap_mode(self, value):
        # accepts_tab cannot be set by users
        assert(False)

    def get_wrap_mode(self):
        return gtk.TextView.get_wrap_mode()

    wrap_mode = gobject.property(
            getter=get_wrap_mode, setter=set_wrap_mode)

    def get_max_line_count(self):
        return self._max_line_count

    def set_max_line_count(self, max_line_count):
        max_line_count = max(1, max_line_count)
        self._max_line_count = max_line_count

        if max_line_count == 1:
            gtk.TextView.set_wrap_mode(self, gtk.WRAP_NONE)
        else:
            gtk.TextView.set_wrap_mode(self, gtk.WRAP_WORD)

        context = self.get_pango_context()
        metrics = context.get_metrics(self.style.font_desc)
        line_height = pango.PIXELS(metrics.get_ascent() + \
                metrics.get_descent())
        self.set_size_request(-1, line_height * max_line_count)

    max_line_count = gobject.property(
            getter=get_max_line_count, setter=set_max_line_count)

    def get_text(self):
        return self._text

    def set_text(self, value):
        self._text = value
        self.props.buffer.props.text = value
        if not self.props.has_focus:
            self._accept()

    text = gobject.property(getter=get_text, setter=set_text)

    def do_size_allocate(self, allocation):
        gtk.TextView.do_size_allocate(self, allocation)
        if not self.props.has_focus:
            self._accept()

    def _accept(self):
        if self._text is None:
            return

        gtk.TextView.set_wrap_mode(self, gtk.WRAP_WORD)

        buf = self.props.buffer
        buf.props.text = self._text

        def accent():
            start = buf.get_start_iter()
            end = buf.get_end_iter()
            buf.apply_tag(self._tag, start, end)

        def last_offset():
            iter = buf.get_start_iter()
            for __ in xrange(self._max_line_count):
                if not self.forward_display_line(iter):
                    return None
            return iter.get_offset()

        accent()
        offset = last_offset()

        if offset is not None:
            offset = len(buf.props.text[:offset].rstrip()) - 1
            buf.props.text = buf.props.text[:offset] + '...'

            final_offset = last_offset()
            if final_offset is not None and final_offset < offset + 3:
                # ellipses added new line
                buf.props.text = buf.props.text[:offset - 3] + '...'

        accent()

    def __button_release_event_cb(self, widget, event):
        buf = self.props.buffer
        if not buf.get_has_selection():
            buf.select_range(buf.get_end_iter(), buf.get_start_iter())
        return False

    def __focus_in_event_cb(self, widget, event):
        self.props.buffer.props.text = self._text

        if self._max_line_count == 1:
            gtk.TextView.set_wrap_mode(self, gtk.WRAP_NONE)
        else:
            gtk.TextView.set_wrap_mode(self, gtk.WRAP_WORD)

        return False

    def __focus_out_event_cb(self, widget, event):
        self._text = self.props.buffer.props.text
        self._accept()
        return False

    def __key_press_event_cb(self, widget, event):
        ignore_mask  = [gtk.keysyms.Return]
        if self._max_line_count == 1:
            ignore_mask.extend([gtk.keysyms.Up, gtk.keysyms.Down])

        if event.keyval in ignore_mask:
            key_event = event
            if event.keyval in [gtk.keysyms.Up]:
                # change Shift mask for backwards keys
                if key_event.state & gtk.gdk.SHIFT_MASK:
                    key_event.state &= ~gtk.gdk.SHIFT_MASK
                else:
                    key_event.state |= gtk.gdk.SHIFT_MASK
            key_event.keyval = gtk.keysyms.Tab
            key_event.hardware_keycode = 0
            gtk.main_do_event(key_event)
            return True

        return False
