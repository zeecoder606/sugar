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
import os
import math

import gtk
import gio
import gobject

from sugar import dispatch
from sugar.util import LRU
from sugar.graphics import style

from jarabe.journal import model


fetched = dispatch.Signal()

THUMB_WIDTH = style.zoom(240)
THUMB_HEIGHT = style.zoom(180)

_CHUNK_SIZE = 1024 * 10 # 10K
_MAX_FILESIZE = 1024 * 1024 * 10 # 10M

_fetch_queue = []


def fetch(offset, metadata):
    entry = _CacheEntry(offset, metadata)

    if entry not in _fetch_queue:
        _fetch_queue.append(entry)
        if len(_fetch_queue) == 1:
            gobject.idle_add(_process_queue)

def discard_queue(visible_range):
    new_queue = []

    for i in _fetch_queue:
        if i.offset in visible_range:
            new_queue.append(i)

    global _fetch_queue
    _fetch_queue = new_queue

def _process_queue():
    while len(_fetch_queue):
        entry = _fetch_queue[0]

        logging.debug('Loading preview for %s', entry.uid)

        if entry.uid.startswith('/'):
            if not os.path.isfile(entry.uid):
                logging.warning('Preview %s is not a file', entry.uid)
                _commit(entry, None)
            elif os.path.getsize(entry.uid) > _MAX_FILESIZE:
                logging.debug('Preview %s is too big to load', entry.uid)
                _commit(entry, None)
            else:
                _AsyncLoader(entry)
        else:
            _load_props(entry)

        break

    return False

def _commit(entry, pixbuf):
    if not _fetch_queue or _fetch_queue[0] != entry:
        logging.debug('Discard %r preview', entry.uid)
    else:
        del _fetch_queue[0]

        if pixbuf is None:
            logging.debug('Empty preview for %s', entry.uid)
        else:
            logging.debug('Ready preview for %s', entry.uid)
            fetched.send(None, offset=entry.offset, pixbuf=pixbuf)

    if len(_fetch_queue):
        gobject.idle_add(_process_queue)

def _load_preview(entry, preview):
    if not preview:
        logging.debug('Empty preview for %s', entry.uid)
        _commit(entry, None)
        return

    if preview[1:4] != 'PNG':
        # TODO: We are close to be able to drop this.
        import base64
        preview = base64.b64decode(preview)

    loader = gtk.gdk.PixbufLoader()
    loader.connect('size-prepared', _size_prepared_cb)

    try:
        loader.write(preview)
    except Exception:
        logging.exception('Can not load preview from metadata for %s',
                entry.uid)
    finally:
        loader.close()

    pixbuf = loader.get_pixbuf()
    if pixbuf is None:
        _commit(entry, None)
    else:
        _commit(entry, pixbuf)

def _load_props(entry):

    def reply_cb(props):
        if props is None:
            _commit(entry, None)
        else:
            _load_preview(entry, props.get('preview'))

    model.get(entry.uid, reply_cb)

def _size_prepared_cb(loader, width, height):
    dest_width = THUMB_WIDTH
    dest_height = THUMB_HEIGHT

    if width == dest_width and height == dest_height:
        return

    ratio_width = float(dest_width) / width
    ratio_height = float(dest_height) / height
    ratio = min(ratio_width, ratio_height)

    # preserve original ration
    if ratio_width != ratio:
        dest_width = int(math.ceil(width * ratio))
    elif ratio_height != ratio:
        dest_height = int(math.ceil(height * ratio))

    loader.set_size(dest_width, dest_height)


class _AsyncLoader(object):

    def __init__(self, entry):
        self._entry = entry

        self._loader = gtk.gdk.PixbufLoader()
        self._loader.connect('size-prepared', _size_prepared_cb)

        self._stream = None
        self._file = gio.File(entry.uid)
        self._file.read_async(self.__file_read_async_cb)

    def __file_read_async_cb(self, input_file, result):
        try:
            self._stream = self._file.read_finish(result)
        except Exception:
            logging.exception('Can not read preview for %s', self._entry.uid)
            _commit(self._entry, None)
            return

        self._stream.read_async(_CHUNK_SIZE, self.__stream_read_async_cb,
                gobject.PRIORITY_LOW)

    def __stream_read_async_cb(self, input_stream, result):
        data = self._stream.read_finish(result)

        if data and self._process_loader(self._loader.write, data):
            self._stream.read_async(_CHUNK_SIZE, self.__stream_read_async_cb,
                    gobject.PRIORITY_LOW)
            return

        if data is None:
            logging.warning('Bad preview data from %s', self._entry.uid)

        self._stream.close()

        if self._process_loader(self._loader.close):
            _commit(self._entry, self._loader.get_pixbuf())
        else:
            _commit(self._entry, None)

    def _process_loader(self, method, *args):
        try:
            method(*args)
        except Exception, e:
            logging.debug('Can not process preview for %s: %r',
                    self._entry.uid, e)
            return False
        else:
            return True

class _CacheEntry(object):
    uid = None
    offset = None

    def __init__(self, offset, metadata):
        self.uid = metadata['uid']
        self.offset = offset

    def __cmp__(self, other):
        return cmp((self.uid, self.offset), (other.uid, other.offset))
