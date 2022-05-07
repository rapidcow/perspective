"""Core classes of for Perspective data types."""

__all__ = ['Panel', 'Entry']

import datetime
import os
import io
from . import timeutil
from . import datatypes


def _assert_type(obj, objtype, name):
    # Used for asserting type for __init__
    if isinstance(obj, objtype):
        return True
    # We shouldn't need __qualname__ if subclass(objtype, type)...
    # Display the module name only if the class is imported
    clsname = (objtype.__name__
               if objtype.__module__ in {'builtins', __name__}
               else f'{objtype.__module__}.{objtype.__name__}')
    article = 'an' if clsname in {'Entry', 'int'} else 'a'
    raise TypeError(f'{name} should be {article} {clsname} object, '
                    f'not {obj!r}')


def _assert_type_or_none(obj, objtype, name):
    if isinstance(obj, objtype):
        return True
    if obj is None:
        return False
    clsname = (objtype.__name__
               if objtype.__module__ in {'builtins', __name__}
               else f'{objtype.__module__}.{objtype.__name__}')
    article = 'an' if clsname in {'Entry'} else 'a'
    raise TypeError(f'{name} should be {article} {clsname} object or None, '
                    f'not {obj!r}')


_NoValue = object()


class Panel:
    """Panel containing entries for a single day."""
    __slots__ = (
        '_date', '_attrs',
        # module-level private reference count
        '_entries',
    )

    def __init__(self, date):
        _assert_type(date, datetime.date, 'date')
        self._date = date
        self._entries = []
        self._attrs = {'rating': None}

    # Create a new panel, copying everything except for the entries
    @classmethod
    def from_panel(cls, panel):
        assert isinstance(panel, Panel)
        obj = cls(panel.date)
        for key, value in panel.get_attribute_dict().items():
            obj.set_attribute(key, value)
        return obj

    def __repr__(self):
        clsname = type(self).__name__
        # use the builtin str() representation of datetime.date
        return '<{} object on {}>'.format(clsname, self.date)

    # Once instantiated, the date cannot be changed.
    @property
    def date(self):
        """Date of the current panel."""
        return self._date

    def entries(self):
        """Get an iterator of the list of entries."""
        return iter(self._entries)

    def get_entries(self):
        """Get a copy of the list of entries."""
        return list(self._entries)

    def add_entry(self, entry):
        """Add an entry to the current panel.

        This will remove the entry from its existing panel (so don't worry
        about calling remove_entry()), and a validation will be performed on
        the entry to check if the date_time is valid.

        The panel attribute of the entry will be changed to self on success.
        """
        if not isinstance(entry, Entry):
            raise TypeError(f'entry should be an Entry object, '
                            f'not {entry!r}')
        if entry.has_panel():
            entry.panel.remove_entry(entry)
        entry._panel = self
        # Make sure proper validation is performed given this new panel.
        # The way we do this though is a bit tricky...
        entry.insight = entry.insight
        self._entries.append(entry)

    def add_entries(self, entries):
        """Call self.add_entry(entry) for each entry in entries."""
        for entry in entries:
            self.add_entry(entry)

    def remove_entry(self, entry):
        """Remove an entry from the current panel.  A ValueError will be
        raised by list.remove() if the entry is not in the current panel.
        """
        self._entries.remove(entry)
        entry._panel = None

    # You could write `entry in panel.get_entries()` and
    # `len(panel.get_entries())`... but like, really?
    # Making a copy every time?
    #
    # (With these methods you can write instead `entry in panel`
    # and panel.n_entries().  "Length of panel" doesn't read well
    # to me and so that's why I didn't define __len__().)
    def __contains__(self, entry):
        return entry in self._entries

    def count(self):
        return len(self._entries)

    # ==========
    # Attributes
    # ==========
    def set_attribute(self, key, value):
        try:
            checker = getattr(self, f'check_{key}_attribute')
        except AttributeError:
            pass
        else:
            value = checker(value)
        self._attrs[key] = value

    def get_attribute(self, key, default=_NoValue):
        if default is _NoValue:
            return self._attrs[key]
        return self._attrs.get(key, default)

    def delete_attribute(self, key):
        if key == 'rating':
            raise ValueError(f'cannot remove {key!r}')
        return self._attrs.pop(key)

    def has_attribute(self, key):
        return key in self._attrs

    def get_attribute_dict(self):
        return self._attrs.copy()

    # --------------------------------------
    # Some attribute checking implementation
    # --------------------------------------
    def check_rating_attribute(self, rating):
        if rating is None:
            return None
        return str(rating)


class Entry:
    """Entry containing text or binary data.
    (Note that date_time must be an aware datetime.datetime object!)
    """
    __slots__ = (
        '_panel', '_date_time', '_insight',
        '_data', '_meta', '_attrs',
    )

    def __init__(self, date_time, *, insight=False):
        self.__check_aware_datetime(date_time)
        self._panel = None

        # These are the only 5 attributes that are always guaranteed to be
        # set... (None means that it is unset)
        self._data = {
            'type': 'binary',
            'format': None,
            'encoding': 'binary',
            'raw': b'',
            'source': None,
        }
        # The following inequalities MUST be true all the time (unless one of
        # these meta attribute is None, i.e. unset):
        #
        #     created <= posted,
        #     created <= modified.
        self._meta = {
            # Posted: The posted time in the Perspective app
            'posted': date_time,
            # Created: The creation time of the file
            'created': None,
            # Modified: The modification time of the file
            'modified': None,
        }
        # Question and caption are not set by default (why? idk..)
        self._attrs = {}

        # panel is None so far so we don't need to call
        # __check_time_and_insight() for validation
        #
        # We're not using the date_time property setter so that subclasses
        # have a chance to make these read-only
        self._insight = bool(insight)
        self._date_time = date_time

    # Help subclasses get the data they need
    # (making a shallow copy of the object doesn't work; the whole object
    # has to be constructed again)
    @classmethod
    def from_entry(cls, entry):
        assert isinstance(entry, Entry)
        # Panel linking will NOT implicitly happen
        obj = cls(entry.date_time)
        obj.insight = entry.insight
        # This sure saves a lot of keystrokes
        for key, value in entry.get_data_dict().items():
            obj.set_data_attribute(key, value)
        for key, value in entry.get_attribute_dict().items():
            obj.set_attribute(key, value)
        for key, value in entry.get_meta_dict().items():
            obj.set_meta_attribute(key, value)
        return obj

    # =================
    # Direct attributes
    # =================
    @property
    def panel(self):
        """Panel that the entry belongs to, None if this entry does not
        belong to a panel.  This attribute can only be changed through
        calling either the remove_entry() method of the parent panel.
        """
        return self._panel

    def has_panel(self):
        """Return self.panel is not None."""
        return self._panel is not None

    @property
    def date_time(self):
        return self._date_time

    @date_time.setter
    def date_time(self, dt):
        self.__check_aware_datetime(dt, 'date_time')
        self.__check_time_and_insight(self.panel, dt, self.insight)
        self._date_time = dt

    @property
    def insight(self):
        """Whether this entry is an insight as a bool."""
        return self._insight

    @insight.setter
    def insight(self, value):
        # Allow implicit truth values
        value = bool(value)
        self.__check_time_and_insight(self.panel, self.date_time, value)
        self._insight = value

    @staticmethod
    def __check_aware_datetime(dt, name):
        _assert_type(dt, datetime.datetime, name)
        if timeutil.is_naive(dt):
            raise TypeError(f'{name} should be an aware datetime object')

    @staticmethod
    def __check_time_and_insight(panel, time, insight):
        if panel is None:
            return
        # Only determine the start of day by the local time zone!
        local_offset = time.utcoffset()
        panel_date = panel.date
        midnight = datetime.time()
        start_of_day = (datetime.datetime.combine(panel_date, midnight)
                        - local_offset)
        time_utc = (time.astimezone(datetime.timezone.utc)
                    .replace(tzinfo=None))

        if time_utc < start_of_day:
            raise ValueError('entry time ({}) earlier than start of day of '
                             'the parent panel ({}) in local time'
                             .format(time, panel_date))

        start_of_insight = start_of_day + datetime.timedelta(days=2)
        if insight and time_utc < start_of_insight:
            raise ValueError('entry is an insight and its time ({}) is '
                             'less than 2 days apart from the start of day '
                             'of the parent panel ({}) in local time'
                             .format(time, panel_date))

    # ====
    # Data
    # ====
    def set_type(self, type):
        _assert_type_or_none(type, str, 'type')
        self._data['type'] = type

    def get_type(self):
        return self._data['type']

    def set_encoding(self, encoding):
        _assert_type_or_none(encoding, str, 'encoding')
        self._data['encoding'] = encoding

    def get_encoding(self):
        return self._data['encoding']

    def set_format(self, format):
        _assert_type_or_none(format, str, 'format')
        self._data['format'] = format

    def get_format(self):
        return self._data['format']

    def has_format(self):
        return self._data['format'] is not None

    def set_raw_data(self, raw):
        _assert_type(raw, bytes, 'raw')
        self._data['raw'] = raw

    def set_data(self, data, *, type='plain', encoding='utf-8'):
        _assert_type(data, str, 'data')
        self._data['raw'] = data.encode(encoding)
        self._data['encoding'] = encoding
        self._data['type'] = type

    def get_raw_data(self):
        """Return the raw binary data of this entry without loading
        the source.
        """
        if self._data['raw'] is not None:
            return self._data['raw']
        if self._data['source'] is not None:
            with io.open(self._data['source'], 'rb') as fp:
                return fp.read()
        raise ValueError('raw data and source path are both unset')

    # slightly modified from basicproc
    def load_data(self):
        """Load the source file into memory if it isn't loaded.
        Return the raw binary data of this entry.
        """
        if self._data['raw'] is not None:
            return self._data['raw']
        content = self.get_raw_data()
        self._data['raw'] = content
        return content

    # BigEntry will reimplement this, where get_data() returns the data from
    # the main file but export() writes a zip archive (to keep the
    # compatibility with the promise of the 'file' argument being a file
    # and not a directory)

    # Get data -> str or bytes
    # (Convenience method)
    def get_data(self):
        if self.is_text():
            return self.get_raw_data().decode(self.get_encoding())
        return self.get_raw_data()

    def has_raw_data(self):
        return self.get_raw_data() is not None

    def set_source(self, path):
        if path is None:
            self._data['source'] = None
            return
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError(f'source path should be str or os.PathLike, '
                            f'not {path!r}')
        try:
            with io.open(path, 'rb') as fp:
                pass
        except OSError as exc:
            if not os.path.exists(path):
                raise ValueError(f'source path {path!r} '
                                 f'does not exist') from exc
            if not os.path.isfile(path):
                raise ValueError(f'source path {path!r} '
                                 f'is not a file') from exc
            # We don't know what caused it... err.....
            raise ValueError(f'invalid source path {path!r}') from exc
        original_path = self._data['source']
        self._data['source'] = path
        # An important thing to note here: users can't set the raw data to
        # None, but we can here.
        self._data['raw'] = None

    def get_source(self):
        return self._data['source']

    def has_source(self):
        return self._data['source'] is not None

    # ==========
    # Attributes
    # ==========
    def set_attribute(self, key, value):
        try:
            checker = getattr(self, f'check_{key}_attribute')
        except AttributeError:
            pass
        else:
            value = checker(value)
        self._attrs[key] = value

    def get_attribute(self, key, default=_NoValue):
        if default is _NoValue:
            return self._attrs[key]
        return self._attrs.get(key, default)

    def delete_attribute(self, key):
        no_delete = ('posted', 'created')
        if key in no_delete:
            raise ValueError(f'cannot delete attributes: {key!r}')
        return self._data.pop(key)

    def has_attribute(self, key):
        return key in self._attrs

    def get_attribute_dict(self):
        return self._attrs.copy()

    # These methods should not exist... but here they are.
    def set_data_attribute(self, key, value):
        if key == 'type':
            self.set_type(value)
        elif key == 'encoding':
            self.set_encoding(value)
        elif key == 'format':
            self.set_format(value)
        elif key == 'data':
            self.set_raw_data(value)
        elif key == 'source':
            self.set_source(value)
        else:
            self._data[key] = value

    def get_data_attribute(self, key, default=_NoValue):
        if default is _NoValue:
            return self._data[key]
        return self._data.get(key, default)

    def delete_data_attribute(self, key):
        no_delete = ('type', 'encoding', 'format', 'data', 'source')
        if key in no_delete:
            raise ValueError(f'cannot delete attribute: {key!r}')
        return self._data.pop(key)

    def has_data_attribute(self, key):
        return key in self._data

    def get_data_dict(self):
        return self._data.copy()

    def set_meta_attribute(self, key, value):
        try:
            checker = getattr(self, f'check_{key}_meta_attribute')
        except AttributeError:
            pass
        else:
            value = checker(value)
        self._meta[key] = value

    def get_meta_attribute(self, key, default=_NoValue):
        if default is _NoValue:
            self._meta[key]
        return self._meta.get(key, default)

    def delete_meta_attribute(self, key):
        no_delete = ('posted',)
        if key in no_delete:
            raise ValueError('cannot delete one of these attributes: {}'
                             .format(', '.join(repr(n) for n in no_delete)))
        return self._meta.pop(key)

    def has_meta_attribute(self, key):
        return key in self._meta

    def get_meta_dict(self):
        return self._meta.copy()

    # --------------------------------------
    # Some attribute checking implementation
    # --------------------------------------
    def check_question_attribute(self, question):
        if question is None:
            return None
        return str(question)

    def check_caption_attribute(self, caption):
        return str(caption)

    def check_posted_meta_attribute(self, posted):
        """The 'posted' meta attribute protocol.
        If `posted` is None, return the time of this object.
        """
        # Posting time should be equal or greater than the entry time.
        # No tolerance is needed as the time without seconds itself is
        # already the lower bound.
        #
        # We accept None for the 'posted' attribute (otherwise the
        # initialization would be way too complicated), although it would
        # always be set when loaded by json_processor.JSONLoader.
        if posted is None:
            return time
        self.__check_aware_datetime(posted, 'posted')
        created = self.get_meta_attribute('created')
        self.__check_created_and_posted_time(created, posted)
        return posted

    def check_created_meta_attribute(self, created):
        """The 'created' meta attribute protocol.
        If `created` is None, return None.
        """
        if created is None:
            return None
        self.__check_aware_datetime(created, 'created')
        posted = self.get_meta_attribute('posted')
        self.__check_created_and_posted_time(created, posted)
        modified = self.get_meta_attribute('modified')
        self.__check_created_and_modified_time(created, modified)
        return created

    def check_modified_meta_attribute(self, modified):
        if modified is None:
            return None
        self.__check_aware_datetime(modified, 'modified')
        created = self.get_meta_attribute('created')
        self.__check_created_and_modified_time(created, modified)
        return modified

    def __check_created_and_posted_time(self, created, posted):
        """Check for created <= posted."""
        if created is None or posted or None:
            return

        # Creation time should be less than or equal to the entry time
        # (by that we mean the posted time on Perspective); when the entry
        # time has 0 seconds and 0 microseconds, creation time should be
        # before the start of the next minute.

        # In case the second value isn't provided (most cases),
        # allow up to 1 minute of difference
        if posted.second == 0 and posted.microsecond == 0:
            tolerance = datetime.timedelta(seconds=60)
        else:
            tolerance = datetime.timedelta(0)
        if timeutil.to_utc(created) > timeutil.to_utc(posted) + tolerance:
            raise ValueError('creation time after time posted')

    def __check_created_and_modified_time(self, created, modified):
        """Check for created <= modified."""
        if created is None or modified is None:
            return
        if timeutil.to_utc(created) > timeutil.to_utc(modified):
            raise ValueError('creation time after modification time')

    def __repr__(self):
        clsname = type(self).__name__
        # use the str() representation of datetime.datetime
        return '<{} object at {}>'.format(clsname, self.date_time)

    # In basicproc.py, this is the is_binary() method.
    # The exact definition of being "binary" isn't so clear, so I decided
    # to negate the term and call it is_text() instead.  It still works
    # exactly the same as `not self.is_binary()` would've.
    def is_text(self):
        """Return True if this entry can be decoded into str, else False.

        More generally speaking, when is_text() returns True, the method
        get_data() guarantees to return a str, else it must return bytes
        of the underlying raw data.
        """
        return self.get_encoding() != 'binary'

    # Note: This will NOT attempt to set the source!
    def export(self, file, *, exist_ok=False):
        """Export the current entry to 'file', raising a FileExistsError
        if it exists (unless exist_ok is True).  This method will NOT update
        the source path.
        """
        mode = 'wb' if exist_ok else 'xb'
        with io.open(file, mode) as fp:
            fp.write(self.get_raw_data())

    def get_raw_data_size(self):
        if self._data['raw'] is not None:
            return len(self._data['raw'])
        if self._data['source'] is not None:
            stat = os.stat(self._data['source'])
            return stat.st_size
        raise ValueError('raw data and source path are both unset')
