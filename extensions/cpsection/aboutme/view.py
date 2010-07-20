# Copyright (C) 2008, OLPC
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import gtk
import gobject
from gettext import gettext as _

from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar.graphics.xocolor import XoColor

from jarabe.controlpanel.sectionview import SectionView
from jarabe.controlpanel.inlinealert import InlineAlert

_DIRECTION_LEFT = 0
_DIRECTION_TOP = 1
_DIRECTION_CENTER = 2
_DIRECTION_BOTTOM = 3
_DIRECTION_RIGHT = 4


class EventIcon(gtk.EventBox):
    __gtype_name__ = "SugarEventIcon"

    def __init__(self, **kwargs):
        gtk.EventBox.__init__(self)

        self.icon = Icon(pixel_size=style.XLARGE_ICON_SIZE, **kwargs)

        self.set_visible_window(False)
        self.set_app_paintable(True)
        self.set_events(gtk.gdk.BUTTON_PRESS_MASK)

        self.add(self.icon)
        self.icon.show()


class ColorPicker(EventIcon):
    __gsignals__ = {
        'color-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([object]))
        }

    def __init__(self, direction):
        EventIcon.__init__(self)

        self.icon.props.icon_name = 'computer-xo'
        self._direction = direction
        self._color = None

        self.icon.props.pixel_size = style.XLARGE_ICON_SIZE

        self.connect('button_press_event', self.__pressed_cb, direction)

    def update(self, color):
        if self._direction == _DIRECTION_CENTER:
            self._color = color
        elif self._direction == _DIRECTION_LEFT:
            self._color = XoColor(color.get_prev_fill_color())
        elif self._direction == _DIRECTION_RIGHT:
            self._color = XoColor(color.get_prev_stroke_color())
        elif self._direction == _DIRECTION_TOP:
            self._color = XoColor(color.get_next_fill_color())
        else:
            self._color = XoColor(color.get_next_stroke_color())
        self.icon.props.xo_color = self._color

    def __pressed_cb(self, button, event, direction):
        if direction != _DIRECTION_CENTER:
            self.emit('color-changed', self._color)


class AboutMe(SectionView):

    def __init__(self, model, alerts):
        SectionView.__init__(self)

        self._model = model
        self.restart_alerts = alerts
        self._nick_sid = 0
        self._color_valid = True
        self._nick_valid = True
        self._handlers = []

        self.set_border_width(style.DEFAULT_SPACING * 2)
        self.set_spacing(style.DEFAULT_SPACING)
        self._group = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self._color_label = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._color_alert = None

        self._pickers = {
                _DIRECTION_CENTER: ColorPicker(_DIRECTION_CENTER),
                _DIRECTION_LEFT: ColorPicker(_DIRECTION_LEFT),
                _DIRECTION_RIGHT: ColorPicker(_DIRECTION_RIGHT),
                _DIRECTION_TOP: ColorPicker(_DIRECTION_TOP),
                _DIRECTION_BOTTOM: ColorPicker(_DIRECTION_BOTTOM)
                }

        self._setup_color()
        initial_color = XoColor(self._model.get_color_xo())
        self._update_pickers(initial_color)

        self._nick_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_alert_box = gtk.HBox(spacing=style.DEFAULT_SPACING)
        self._nick_entry = None
        self._nick_alert = None
        self._setup_nick()
        self.setup()

    def _setup_nick(self):
        self._nick_entry = gtk.Entry()
        self._nick_entry.modify_bg(gtk.STATE_INSENSITIVE,
                                   style.COLOR_WHITE.get_gdk_color())
        self._nick_entry.modify_base(gtk.STATE_INSENSITIVE,
                                     style.COLOR_WHITE.get_gdk_color())
        self._nick_entry.set_width_chars(25)
        self._nick_box.pack_start(self._nick_entry, expand=False)
        self._nick_entry.show()

        label_entry_error = gtk.Label()
        self._group.add_widget(label_entry_error)
        self._nick_alert_box.pack_start(label_entry_error, expand=False)
        label_entry_error.show()

        self._nick_alert = InlineAlert()
        self._nick_alert_box.pack_start(self._nick_alert)
        if 'nick' in self.restart_alerts:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_alert.show()

        self._center_in_panel = gtk.Alignment(0.5)
        self._center_in_panel.add(self._nick_box)
        self.pack_start(self._center_in_panel, False)
        self.pack_start(self._nick_alert_box, False)
        self._nick_box.show()
        self._nick_alert_box.show()
        self._center_in_panel.show()

    def _setup_color(self):
        label_color = gtk.Label(_('Click to change your color:'))
        label_color.modify_fg(gtk.STATE_NORMAL,
                              style.COLOR_SELECTION_GREY.get_gdk_color())
        self._group.add_widget(label_color)
        self._color_label.pack_start(label_color, expand=False)
        label_color.show()

        for direction in sorted(self._pickers.keys()):
            if direction == _DIRECTION_CENTER:
                left_separator = gtk.SeparatorToolItem()
                left_separator.show()
                self._color_box.pack_start(left_separator, expand=False)

            picker = self._pickers[direction]
            picker.show()
            self._color_box.pack_start(picker, expand=False)

            if direction == _DIRECTION_CENTER:
                right_separator = gtk.SeparatorToolItem()
                right_separator.show()
                self._color_box.pack_start(right_separator, expand=False)

        label_color_error = gtk.Label()
        self._group.add_widget(label_color_error)
        self._color_alert_box.pack_start(label_color_error, expand=False)
        label_color_error.show()

        self._color_alert = InlineAlert()
        self._color_alert_box.pack_start(self._color_alert)
        if 'color' in self.restart_alerts:
            self._color_alert.props.msg = self.restart_msg
            self._color_alert.show()

        self._center_in_panel = gtk.Alignment(0.5)
        self._center_in_panel.add(self._color_box)
        self.pack_start(self._color_label, False)
        self.pack_start(self._center_in_panel, False)
        self.pack_start(self._color_alert_box, False)
        self._color_label.show()
        self._color_box.show()
        self._color_alert_box.show()
        self._center_in_panel.show()

    def setup(self):
        self._nick_entry.set_text(self._model.get_nick())
        self._color_valid = True
        self._nick_valid = True
        self.needs_restart = False

        def connect(widget, signal, cb):
            self._handlers.append((widget, widget.connect(signal, cb)))

        connect(self._nick_entry, 'changed', self.__nick_changed_cb)
        for picker in self._pickers.values():
            connect(picker, 'color-changed', self.__color_changed_cb)

    def undo(self):
        for widget, handler in self._handlers:
            widget.disconnect(handler)
        self._model.undo()
        self._nick_alert.hide()
        self._color_alert.hide()

    def _update_pickers(self, color):
        for picker in self._pickers.values():
            picker.update(color)

    def _validate(self):
        if self._nick_valid and self._color_valid:
            self.props.is_valid = True
        else:
            self.props.is_valid = False

    def __nick_changed_cb(self, widget, data=None):
        if self._nick_sid:
            gobject.source_remove(self._nick_sid)
        self._nick_sid = gobject.timeout_add(self._APPLY_TIMEOUT,
                                             self.__nick_timeout_cb, widget)

    def __nick_timeout_cb(self, widget):
        self._nick_sid = 0

        if widget.get_text() == self._model.get_nick():
            return False
        try:
            self._model.set_nick(widget.get_text())
        except ValueError, detail:
            self._nick_alert.props.msg = detail
            self._nick_valid = False
        else:
            self._nick_alert.props.msg = self.restart_msg
            self._nick_valid = True
            self.needs_restart = True
            self.restart_alerts.append('nick')
        self._validate()
        self._nick_alert.show()
        return False

    def __color_changed_cb(self, colorpicker, color):
        self._model.set_color_xo(color.to_string())
        self.needs_restart = True
        self._color_alert.props.msg = self.restart_msg
        self._color_valid = True
        self.restart_alerts.append('color')

        self._validate()
        self._color_alert.show()

        self._update_pickers(color)

        return False
