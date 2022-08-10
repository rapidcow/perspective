"""Core classes of for Perspective data types."""

__all__ = ['Panel', 'Entry', 'Configurable']

import copy
import datetime
import io
import os
from . import timeutil
from . import util


def _assert_type(obj, objtype, name, article='a'):
    # Used for asserting types for user values
    if isinstance(obj, objtype):
        return True
    clsname = objtype.__qualname__
    raise TypeError(f'{name} should be {article} {clsname}, '
                    f'not {obj!r}')


def _assert_type_or_none(obj, objtype, name, article='a'):
    if isinstance(obj, objtype):
        return True
    if obj is None:
        return False
    clsname = objtype.__qualname__
    raise TypeError(f'{name} should be {article} {clsname} '
                    f'or None, not {obj!r}')


_NoValue = object()
# buffer size for comparing entry data
BUFSIZE = 8192


class _AttributeHolder:
    """Private base class for Panel and Entry.
    The constructor takes no positional or keyword argument.
    """
    __slots__ = ('_attrs',)

    def get_attribute(self, name, /, default=_NoValue):
        """Get the attribute with 'name'.
        Raise KeyError if 'name' is not an attribute,
        unless 'default' is provided, in which case return 'default'.
        """
        try:
            attrs = self._attrs
        except AttributeError:
            if default is _NoValue:
                raise KeyError(name) from None
            return default
        if default is _NoValue:
            return attrs[name]
        return attrs.get(name, default)

    def set_attribute(self, name, value, /):
        """Set the attribute to 'value' with 'name'."""
        try:
            attrs = self._attrs
        except AttributeError:
            self._attrs = attrs = {}
        attrs[name] = value

    def delete_attribute(self, name, /):
        """Delete the attribute with 'name', returning the original value.
        Raise KeyError if 'name' is not an attribute.
        """
        try:
            attrs = self._attrs
        except AttributeError:
            raise KeyError(name) from None
        return attrs.pop(name)

    def has_attribute(self, name, /):
        """Return whether the current object has an attribute with 'name'."""
        try:
            attrs = self._attrs
        except AttributeError:
            return False
        return name in attrs

    def get_attribute_names(self, /):
        """Return a set of all attribute names."""
        try:
            attrs = self._attrs
        except AttributeError:
            attrs = {}
        return attrs.keys()

    def get_attribute_items(self, /):
        """Return an iterator of name-value pairs of all attributes."""
        try:
            attrs = self._attrs
        except AttributeError:
            attrs = {}
        return attrs.items()

    def get_attributes(self, /):
        """Return a dict of the attributes."""
        try:
            attrs = self._attrs
        except AttributeError:
            return {}
        return attrs.copy()

    def set_attributes(self, /, *args, **kwargs):
        """Use 'dict.update()' to set attributes for this current object."""
        try:
            attrs = self._attrs
        except AttributeError:
            self._attrs = attrs = {}
        attrs.update(*args, **kwargs)


class Panel(_AttributeHolder):
    """Panel containing entries for a single day.

    Parameter
    ---------
    date : datetime.date object
        Date of the panel.  Will be accessible from the 'panel' property.
    """
    __slots__ = ('_date', '_entries')

    def __init__(self, date, /):
        super().__init__()
        _assert_type(date, datetime.date, 'date')
        self._date = date
        self._entries = []

    # Create a new panel, copying everything except for the entries
    @classmethod
    def from_panel(cls, panel):
        """Create a new panel object from the date and attributes of
        'panel'.  Note that the new panel will hold no entries from 'panel'.
        """
        if not isinstance(panel, Panel):
            raise TypeError('panel must be a Panel object')
        obj = cls(panel.date)
        for name, value in panel.get_attribute_items():
            obj.set_attribute(name, copy.deepcopy(value))
        return obj

    def copy(self):
        """Return a deep copy of this panel with no entries.
        Equivalent to self.from_panel(self).
        """
        return self.from_panel(self)

    def __repr__(self):
        # use the builtin str() representation of datetime.date
        return f'<{type(self).__name__} object on {self.date}>'

    # Once instantiated, the date cannot be changed.
    @property
    def date(self):
        """Date of the current panel."""
        return self._date

    def entries(self):
        """Get an iterator of the list of entries."""
        yield from self._entries

    def get_entry(self, index):
        """Get an entry with index."""
        return self._entries[index]

    def get_entries(self):
        """Get a copy of the list of entries."""
        return self._entries.copy()

    def add_entry(self, entry):
        """Add 'entry' to the current panel.

        This will remove 'entry' from its existing panel (so don't worry
        about calling remove_entry()), and a validation will be performed on
        the entry to check if the date_time is valid.  This is a ValueError
        if 'entry' is added.

        The panel attribute of the entry will be changed to self on success.
        """
        if self.has_entry(entry):
            raise ValueError(f'entry was added')
        if not isinstance(entry, Entry):
            raise TypeError(f'entry should be an Entry object, '
                            f'not {entry!r}')
        if entry.has_panel():
            entry.panel.remove_entry(entry)
        # Make sure proper validation is performed given this new panel.
        entry._set_panel(self)
        self._entries.append(entry)

    def remove_entry(self, entry):
        """Remove 'entry' from the current panel.  A ValueError will be
        raised by list.remove() if the entry is not in the current panel.
        """
        # DON'T USE list.remove()!!!  That will remove the first occurrence
        # of an object EQUAL to entry, not IDENTICAL to entry.
        for i, item in enumerate(self._entries):
            if item is entry:
                del self._entries[i]
                entry._set_panel(None)
                return
        raise ValueError(f'entry {entry!r} is not in this panel')

    def pop_entry(self, index=-1):
        """Remove an entry from the current panel at 'index' and return it.
        An IndexError will be raised by list.pop() if the index is out of
        bounds.
        """
        entry = self._entries.pop(index)
        entry._panel = None
        return entry

    # You could write `entry in panel.get_entries()` and
    # `len(panel.get_entries())`... but like, really?
    # Making a copy every time?
    #
    # (With these methods you can write instead `if entry in panel`
    # and `panel.count()` and `if panel.has_entries()`...)

    ### DEPRECATED (membership checks for == too, which is not what we want)
    # def __contains__(self, entry):
    #     """Return True if `entry` is an entry of this panel."""
    #     return entry in self._entries

    def count(self):
        """Return the number of entries in this panel."""
        return len(self._entries)

    def has_entries(self):
        """Return True if there is at least one entry."""
        # I read about the performance here and it says ternary operator
        # is the fastest?  https://stackoverflow.com/a/13265186
        return True if self._entries else False

    def has_entry(self, entry):
        return any(e is entry for e in self._entries)

    def sort_entries(self, *, key=None, reverse=False):
        """Call list.sort() on the internal entry list."""
        return self._entries.sort(key=key, reverse=reverse)

    # See below on __eq__().
    def __eq__(self, other):
        """Return self == other.  If other is an instance of Panel,
        True is returned if the date, attributes, and entries are
        all equal.
        """
        # We accept objects of any subclass of Panel
        if isinstance(other, Panel):
            if not (self.date == other.date
                    and self.get_attributes() == other.get_attributes()):
                return False
            # Subclasses should override __eq__() too if they want to
            # rewire the entries list somehow!
            return self._entries == other._entries
        return NotImplemented

    # Perspective day rating
    # ----------------------
    # There is no strict validation, but I personally represent the
    # three ratings in the app with ':(', ':|', and ':)'.
    def get_rating(self, *args, **kwargs):
        """Get the rating for this panel.  KeyError is raised if
        this panel has no rating, unless a default is provided,
        in which case that default is returned.
        """
        return self.get_attribute('rating', *args, **kwargs)

    def set_rating(self, rating):
        """Set the rating for this panel.  rating must be a str."""
        _assert_type(rating, str, 'rating')
        self.set_attribute('rating', rating)

    def delete_rating(self):
        """Delete the rating for this panel and return it.
        KeyError is raised if this panel has no rating.
        """
        return self.delete_attribute('rating')

    def has_rating(self):
        """Return whether this panel has a rating."""
        return self.has_attribute('rating')

    # Extensions
    def __init_subclass__(cls, extname=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if extname is not None:
            cls._extname = extname
        else:
            cls._extname = cls.__name__

    @classmethod
    def get_extension_name(cls):
        """Return extension name for the current panel class.
        (Don't call this class method on Panel itself!)
        """
        return cls._extname


# Validation for Entry
_TWO_DAYS = datetime.timedelta(2)
_UTC = datetime.timezone.utc

def _check_aware_datetime(dt, name):
    _assert_type(dt, datetime.datetime, name)
    if timeutil.is_naive(dt):
        raise TypeError(f'{name} should be an aware datetime object')


def _check_time_and_insight(panel, time, insight):
    if panel is None:
        return
    # Actually we don't even need to look at the time zone;
    # just comaring the date is enough :L
    panel_date = panel.date
    entry_date = time.date()

    if entry_date < panel_date:
        raise ValueError(f'entry time ({time}) earlier than start of day '
                         f'of the parent panel ({panel_date}) in local time')

    # Insight entries have to be at least two days apart, with
    # an exception for the weekly evaluation on Sundays on any of
    # any of the seven days prior to it.
    if (insight
            and entry_date < panel_date + _TWO_DAYS
            and not (entry_date.weekday() == 6 and entry_date != panel_date)):
        raise ValueError(f'entry is an insight and its time ({time}) is '
                         f'less than 2 days apart from the start of day '
                         f'of the parent panel ({panel_date}) in local time')


class Entry(_AttributeHolder):
    """Entry containing text or binary data.
    (Note that time must be an aware datetime.datetime object!)
    """
    __slots__ = (
        '_panel', '_date_time', '_insight',
        '_type', '_format', '_encoding', '_raw', '_source',
    )

    def __init__(self, time, /, insight=False):
        super().__init__()
        _check_aware_datetime(time, 'time')
        self._panel = None

        self._type = 'binary'
        self._format = None
        self._encoding = 'binary'
        # Whether 'raw' is None determines whether this entry stores
        # data from a file or in memory.
        #
        # 'raw' is always preferred to 'source' by get_raw_data(),
        # although 'source' may be set when 'raw' is set too (by calling
        # the 'load_data()' method after 'set_source()' is called at some
        # point; my HOPE is to speed up the data retrival somehow...)
        # When set_raw_data() is called 'source' is automatically
        # discarded, so beware of that.
        #
        # See: TestEntry.test_raw_data_and_source() in tests/test_types.py
        self._raw = b''
        self._source = None

        # panel is None so far so we don't need to call
        # _check_time_and_insight() for validation
        #
        # We're not using the time property setter so that subclasses
        # have a chance to make these read-only
        self._insight = bool(insight)
        self._date_time = time

    # Help subclasses get the data they need
    # (making a shallow copy of the object doesn't work; the whole object
    # has to be constructed again)
    @classmethod
    def from_entry(cls, entry):
        """Create a new entry object from the time, insight, data attributes,
        and attributes of 'entry'.
        """
        if not isinstance(entry, Entry):
            raise TypeError('entry must be an Entry object')
        obj = cls(entry.time, entry.insight)
        # XXX: bypass every validation to increase the likelihood
        # of success???
        obj._type = entry._type
        obj._format = entry._format
        obj._encoding = entry._encoding
        obj._raw = entry._raw
        obj._source = entry._source
        for name, value in entry.get_attribute_items():
            obj.set_attribute(name, copy.deepcopy(value))
        return obj

    def copy(self):
        """Return a deep copy of this entry.  Equivalent to
        self.from_entry(self).
        """
        return self.from_entry(self)

    @property
    def panel(self):
        """Panel that the entry belongs to; None if this entry does not
        belong to a panel.  This attribute can only be changed through
        calling either the remove_entry() method of the parent panel
        or the add_entry() method of a new panel.
        """
        return self._panel

    def has_panel(self):
        """Return self.panel is not None."""
        return self._panel is not None

    def _set_panel(self, panel):
        """USERS SHOULD NOT USE THIS METHOD!  Panel calls this method
        internally to set self._panel and call appropriate validation
        function.
        """
        # Set the panel only after we finished the validation
        _check_time_and_insight(panel, self.time, self.insight)
        self._panel = panel

    # this used to be date_time for a VERY VERY LONG time...
    # so if that confused you, well... :/
    @property
    def time(self):
        """Time of the entry."""
        return self._date_time

    @time.setter
    def time(self, dt):
        _check_aware_datetime(dt, 'time')
        _check_time_and_insight(self.panel, dt, self.insight)
        self._date_time = dt

    @property
    def insight(self):
        """Boolean for whether this entry is an insight."""
        return self._insight

    @insight.setter
    def insight(self, value):
        # no we don't allow implicit bool values like wtf
        _assert_type(value, bool, 'insight')
        _check_time_and_insight(self.panel, self.time, value)
        self._insight = value

    # ====
    # Data
    # ====
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

    def set_type(self, type):
        """Set the type of this entry.  type must be a str."""
        _assert_type(type, str, 'type')
        self._type = type

    def get_type(self):
        """Get the type of this entry."""
        return self._type

    def set_encoding(self, encoding):
        """Set the encoding of this entry.  encoding must be a str."""
        _assert_type(encoding, str, 'encoding')
        self._encoding = encoding

    def get_encoding(self):
        """Get the encoding of the entry."""
        return self._encoding

    def set_format(self, format):
        """Set the format of the entry.  format must be a str or None."""
        _assert_type_or_none(format, str, 'format')
        self._format = format

    def get_format(self):
        """Get the format of this entry."""
        return self._format

    def has_format(self):
        """Return whether this entry has format.  Equivalent to
        self.get_format() is not None.
        """
        return self.get_format() is not None

    def set_raw_data(self, raw):
        """Set the raw data of this entry.  raw must be a bytes object.
        Source is set to None immediately after raw data is successfully set.
        """
        _assert_type(raw, bytes, 'raw')
        self._raw = raw
        self._source = None

    def get_raw_data(self):
        """Get the raw binary data of this entry as a bytes object."""
        if self._raw is not None:
            return self._raw
        with io.open(self._source, 'rb') as fp:
            return fp.read()

    def get_raw_data_size(self):
        """Return the number of bytes of the raw data."""
        if self.has_source():
            stat = os.stat(self._source)
            return stat.st_size
        return len(self._raw)

    def set_data(self, text, type='plain', encoding='utf-8'):
        """Convenience method for setting this entry's data to some text.

        Parameters
        ----------
        text : str
            The text data to set for this entry.

        type : str, default 'plain'
            The type to set for this entry.

        encoding : str, default 'utf-8'
            The encoding to encode the text with and set to this
            entry using self.set_encoding().
        """
        _assert_type(text, str, 'text data')
        self.set_raw_data(text.encode(encoding))
        self.set_encoding(encoding)
        self.set_type(type)

    # Get data -> str or bytes
    # (Convenience method)
    def get_data(self):
        """Get text/binary data of this entry.  If this entry is a text
        entry, raw data is decoded to a string and returned.  Otherwise
        this is equivalent to self.get_raw_data().
        """
        if self.is_text():
            return self.get_raw_data().decode(self.get_encoding())
        return self.get_raw_data()

    def get_source(self):
        """Get the path to source file of this entry."""
        return self._source

    def has_source(self):
        """Return whether this entry has a source file.  Equivalent to
        self.get_source() is not None.
        """
        return self.get_source() is not None

    def set_source(self, path):
        """Set the source file of this entry.  'path' must be a path-like
        object.
        """
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError(f'source should be str or os.PathLike, '
                            f'not {path!r}')
        self._source = path
        # An important thing to note here: users can't set the raw data to
        # None, but we can here.
        self._raw = None

    def __repr__(self):
        # use the str() representation of datetime.datetime
        return f'<{type(self).__name__} object at {self.time}>'

    # At first I didn't really think of implementing this, but well... let's
    # just say simply comparing the attributes + type + format + get_data()
    # isn't general enough to encapsulate all cases (big entries, for
    # instance, can be different even when get_data() remains the same.)
    #
    # Furthermore it seems like that Entry was gonna be hashable according to
    # https://docs.python.org/3/reference/datamodel.html#object.__hash__!
    # But that doesn't make sense since entries are mutable!
    # Implementing __eq__() removes __hash__() and makes Entry unhashable.
    def __eq__(self, other):
        # We accept objects of any subclass of Entry
        if isinstance(other, Entry):
            self_utctime = self.time.astimezone(_UTC)
            other_utctime = other.time.astimezone(_UTC)
            if not (self_utctime == other_utctime
                    and self.insight == other.insight):
                return False
            # Compare data type and format
            if not (self.get_type() == other.get_type()
                    and self.get_format() == other.get_format()):
                return False
            # Compare actual data
            #   Two entries that are not both text or binary are
            #   never equal.
            if self.is_text() != self.is_text():
                return False
            if self.get_attributes() != other.get_attributes():
                return False
            #   Note that we don't require the data to be byte-wise
            #   equal if they are text.
            with self.stream_data() as fp1:
                with other.stream_data() as fp2:
                    return util.fileobjequal(fp1, fp2)
        return NotImplemented

    # Live streamers
    def stream_raw_data(self):
        """Return a file-like object that implements read().
        Note that THE CALLER IS RESPONSIBLE FOR CLOSING IT.
        """
        if self.has_source():
            return io.open(self.get_source(), 'rb')
        return io.BytesIO(self.get_raw_data())

    def stream_data(self):
        """Return a file-like object that implements read().
        Depending on whether the entry is a text entry or not,
        the read() method returns either str or bytes.
        Note that THE CALLER IS RESPONSIBLE FOR CLOSING IT.
        """
        if self.is_text():
            if self.has_source():
                return io.open(self.get_source(),
                               encoding=self.get_encoding())
            return io.StringIO(self.get_data())
        return self.stream_raw_data()

    # Perspective question
    def get_question(self, *args, **kwargs):
        """Get the question for this entry.  KeyError is raised if
        this entry has no question, unless a default is provided,
        in which case that default is returned.
        """
        return self.get_attribute('question', *args, **kwargs)

    def set_question(self, question):
        """Set the question for this entry.  question must be a str."""
        _assert_type(question, str, 'question')
        self.set_attribute('question', question)

    def delete_question(self):
        """Delete the question for this entry and return it.
        KeyError is raised if this entry has no question.
        """
        return self.delete_attribute('question')

    def has_question(self):
        """Return whether this entry has a question."""
        return self.has_attribute('question')

    # A method to provide alternative name for subclasses
    # (name clash can happen, but at least the program won't crash XD)
    def __init_subclass__(cls, extname=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if extname is not None:
            cls._extname = extname
        else:
            cls._extname = cls.__name__

    @classmethod
    def get_extension_name(cls):
        """Return extension name for the current entry class.
        (Don't call this class method on Entry itself!)
        """
        return cls._extname


class Configurable:
    """Base class for classes that have options."""
    __slots__ = ('_options',)

    def __new__(cls, *args, **kwargs):
        if cls is Configurable:
            raise TypeError('Configurable must be subclassed')
        return super().__new__(cls)

    def __init__(self):
        super().__init__()
        self._options = {}
        for name, value in type(self)._default_options.items():
            self._options[name] = copy.deepcopy(value)

    def get_option(self, name):
        """Get the value of the option with 'name'.  Raise KeyError if
        'name' is not an existing option for this instance.
        """
        return self._options[name]

    def set_option(self, name, value):
        """Set the option with 'name' to value.  Raise ValueError if 'name'
        is not an existing option for this instance.
        """
        if name not in self._options:
            raise ValueError(f'invalid option name for '
                             f'{type(self).__qualname__}: {name!r}')
        try:
            checker = type(self)._hooks[name]
        except KeyError:
            pass
        else:
            value = checker(self, name, value)
        self._options[name] = value

    def has_option(self, name):
        """Return whether this instance has the option named 'name'."""
        return name in self._options

    def get_option_names(self):
        """Return a set of all option names for this instance."""
        return self._options.keys()

    def configure(self, **kwargs):
        """Set option with the name and value of every keyword argument.
        This method calls set_option() for every keyword argument.
        """
        for name, value in kwargs.items():
            self.set_option(name, value)

    @classmethod
    def add_option(cls, name, default, hook=None):
        """Register an option named 'name' with a default value of
        'default'.  An optional hook can be supplied as a callback function
        which will be called with two arguments (self, value) every time the
        user attempts to set an option.
        """
        if name in cls._default_options:
            raise ValueError(f'option {name!r} is already registered')
        cls._default_options[name] = default
        if hook is not None:
            cls._hooks[name] = hook

    @classmethod
    def is_option_registered(cls, name):
        """Return whether the option has been registered."""
        return name in cls._default_options

    @classmethod
    def remove_option(cls, name):
        """Unregister an option named 'name'.  Return a tuple of the default
        value and the hook function on success (if the option does not have
        a hook, None takes the place of the hook).  KeyError is raised if
        'name' is not registered.
        """
        default = cls._default_options.pop(name)
        checker = cls._hooks.pop(name, None)
        return default, checker

    @classmethod
    def get_registered_option_names(cls):
        """Return a set of all registered option names."""
        return cls._default_options.keys()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._default_options = defaults = {}
        cls._hooks = hooks = {}
        # Traverse the MRO in reversed order, skipping
        # only the current class.
        for base in cls.__mro__[:0:-1]:
            if issubclass(base, Configurable) and base is not Configurable:
                defaults.update(base._default_options)
                hooks.update(base._hooks)
