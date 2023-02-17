"""Processor for JSON archives."""

import base64
import collections
import datetime
import fnmatch
import glob
import io
import itertools
import json
import os
import shutil

from ..types import Panel, Entry
from ..types import Configurable
from .. import filetypes
from .. import timeutil
from .. import util

__all__ = [
    'JSONLoader', 'JSONDumper', 'load_json', 'dump_json',
    'LoadError', 'DumpError', 'LoadWarning', 'DumpWarning',
    'find_paths', 'get_lookup_paths', 'InferenceManager',
]


class LoadError(ValueError):
    """Error that occured while loading a JSON file."""


class LoadWarning(UserWarning):
    """Warning that occured while loading a JSON file."""


class DumpError(ValueError):
    """Error that occured while dumping a JSON file."""


class DumpWarning(UserWarning):
    """Warning that occured while dumping a JSON file."""


# This is a class now... yippee! XD
class InferenceManager:
    """Manager of the inference rules."""
    __slots__ = ()

    def alias_check(self, name):
        """Return the name of a file type if `type` is an alias of
        it, else return `type`.
        """
        return filetypes.get_context().alias_check(name)

    def infer_type_from_encoding(self, enc):
        """Infer file type from encoding.  enc is None if user didn't
        provide a value, otherwise it is a str.  This method should
        return a str or None upon failure.
        """
        if enc is None:
            return None
        return 'binary' if enc == 'binary' else 'plain'

    def infer_encoding_from_type(self, type):
        """Infer encoding from file type.  type is a str.
        This method should return a str or None upon failure.  The str
        should be precisely 'binary' for a binary file and any other
        str for a text file.
        """
        ctx = filetypes.get_context()
        try:
            is_text = ctx.is_text_type(type)
        except LookupError:
            return None
        return 'utf-8' if is_text else 'binary'

    def infer_type_from_path(self, filepath):
        """Infer file type from file path.  filepath is a str.
        This method should return a str when inference is successful
        or return None upon failure.
        """
        ctx = filetypes.get_context()
        parts = os.path.basename(filepath).split('.')
        # The part after a leading dot is not an extension
        if parts and not parts[0]:
            del parts[0]
        # Strip out the file name part.  The rest are all going to be
        # tested for extension.
        extparts = collections.deque(f'.{part}' for part in parts[1:])
        # Prefer the longest possible extension to shorter ones
        while extparts:
            try:
                return ctx.extension_to_type(''.join(extparts))
            except LookupError:
                extparts.popleft()
        return None


# JSON field validators (not public, but could be helpful :/)
def _assert_type(obj, objtype, key, article='a', extra=''):
    """Assert that `obj` has type `objtype`, else raise a TypeError
    exception.

    Parameter
    ---------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    article : str, default 'a'
        Article to use before the object type.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.
    """
    if isinstance(obj, objtype):
        return
    keyname = f'{key!r}{extra}'
    typename = objtype.__name__
    clsname = type(obj).__name__
    raise TypeError(f'{keyname}: expected {article} {typename}, '
                    f'got {clsname}')


def _assert_type_or_none(obj, objtype, key, article='a', extra=''):
    """Assert that `obj` has type `objtype` or is None (JSON null),
    else raise a TypeError exception.

    Parameters
    ----------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    article : str, default 'a'
        Article to use before the object type.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.

    Return
    ------
    obj is not None.
    """
    if isinstance(obj, objtype):
        return True
    if obj is None:
        return False
    keyname = f'{key!r}{extra}'
    typename = objtype.__name__
    clsname = type(obj).__name__
    raise TypeError(f'{keyname}: expected {article} {typename} or None, '
                    f'got {clsname}')


def _assert_list_type(obj, item_type, key, extra=''):
    """Assert that `obj` is a list (JSON array) of objects of type
    `item_type`, else raise a TypeError exception.

    Parameters
    ----------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.
    """
    _assert_type(obj, list, key, extra)
    for i, item in enumerate(obj, start=1):  # hooman index
        if isinstance(item, item_type):
            continue
        header = repr(key) if extra is None else f'{key!r}{extra}'
        typename = item_type.__name__
        clsname = type(obj).__name__
        raise TypeError(f'{header}: expected a list of {typename}, '
                        f'found item {i} to be an instance of {clsname}')


def _ensure_text(obj, key, extra=''):
    """Assert that `obj` is either a string or a list (JSON array) of
    strings, and return the concatenated string.

    Parameters
    ----------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.

    Return
    ------
    A mushed string uwu
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        try:
            return ''.join(obj)
        except TypeError:
            # We already know there's something wrong in the list, so
            # let _assert_list_type() raise that error for us...
            _assert_list_type(obj, str, key, extra)
            # or just in case...
            raise
    header = f'{key!r}{extra}'
    clsname = type(obj).__name__
    raise TypeError(f'{header}: expected a str or a list of str, '
                    f'got {clsname!r}')


# Namespace for the panel/entry classes created by make_*_class()
_class_ns = {'__slots__': ()}


class JSONLoader(Configurable):
    """A JSON archive loader.

    The constructor takes no positional arguments; all keyword
    arguments are passed to the `configure()` method.
    """
    __slots__ = ('_inference_manager',)

    def __init__(self, **options):
        super().__init__()
        self.configure(**options)

    def get_inference_manager(self):
        """Get the inference manager for this loader."""
        try:
            return self._inference_manager
        except AttributeError:
            self._inference_manager = InferenceManager()
            return self._inference_manager

    def set_inference_manager(self, manager, /):
        """Set the inference manager for this loader."""
        self._inference_manager = manager

    def _warn(self, msg, w):
        """Raise an exception with w(msg) if the `error_on_warning` option
        is set to True, else issue an warning.

        The `suppress_warnings` option overrides everything.
        """
        if self.get_option('suppress_warnings'):
            return
        if self.get_option('error_on_warning'):
            raise w(msg)
        import warnings
        warnings.warn(msg, w, 2)

    def load(self, fp):
        """Load an archive from a file object and return the panels.

        If `date` is provided, optimize the loading process by only
        returning the panel on that date.

        Parameters
        ----------
        fp : file object
            A file-like object that implements a read().

        Return
        ------
        A generator of panels, same as load_data().
        """
        data = self.load_json(fp)
        return self.load_data(data)

    def load_json(self, fp):
        """Load a JSON archive from a file object and return a dict."""
        return json.load(fp, **self.get_option('json_options'))

    def load_data(self, data):
        """Load an archive from a dict and return a generator of panels.

        Parameters
        ----------
        data : dict
            The JSON archive.

        Return
        ------
        A generator of panels.
        """
        panels, attrs = self.split_data(data)
        hist = collections.deque(maxlen=2)

        check_panel_order = self.get_option('check_panel_order')
        check_entry_order = self.get_option('check_entry_order')
        for index, panel_dict in enumerate(panels, start=1):
            panel = self.process_panel(panel_dict.copy(), attrs)
            hist.append(panel)
            if check_panel_order:
                # Hooman index!  Maybe?
                self.__check_panel_order(hist, index)
            if check_entry_order:
                self.__check_entry_order(panel, index)
            yield panel

    def split_data(self, data):
        """Split a dict representing a JSON archive into (panels, attrs).

        'panels' is a list of panels, each of which is passed to
        process_panel().  'attrs' is the top-level attributes.
        Default implementation takes 'panels' from the 'data' key,
        while 'attrs' is everything else other than 'data'.

        Note that while split_data() operates on a shallow copy of
        'data', 'panels' is a reference to the original list.
        """
        # The name might be a bit misleading since it doesn't actually
        # simply "split" the data (since we're not returning the
        # attributes and so it remains a local variable to us).
        if not isinstance(data, dict):
            raise TypeError('JSON data should be a dict')
        data = data.copy()
        try:
            panels = data.pop('data')
            _assert_list_type(panels, dict, 'data')
        except KeyError:
            panels = []

        # The rest of 'data' are attributes.  (At least this allows
        # subclasses to do weird stuff to them)
        attrs = data

        if 'paths' in attrs:
            _assert_list_type(attrs['paths'], str, 'paths')
        else:
            attrs['paths'] = ['.']

        if 'tz' in attrs:
            _assert_type(attrs['tz'], str, 'tz', 'top level')
        else:
            attrs['tz'] = None

        return panels, attrs

    def process_panel(self, panel, attrs):
        """Process a JSON object representing a panel.

        Parameters
        ----------
        panel : dict
            The JSON object (dict) to be processed.

        attrs : dict
            Attributes such as the time zone and lookup paths.

        Return
        ------
        A Panel object.  This may return None, in which case
        load_data() will skip the panel (and return None if date
        is explicitly passed to it).
        """
        extensions = self.get_panel_extensions(panel, attrs)
        panel_class = self.make_panel_class(extensions)
        return self.make_panel(panel_class, panel, attrs)

    def get_panel_extensions(self, panel, attrs):
        """Get a list of `Panel` subclasses, with the first base class
        coming last in the list.
        """
        return []

    def make_panel_class(self, extensions):
        """Create a `Panel` class with the `extensions` list
        reversed as the bases.
        """
        if not extensions:
            return Panel
        bases = list(extensions)
        extnames = ', '.join(cls.get_extension_name() for cls in bases)
        bases.reverse()
        bases.append(Panel)
        return type(f'Panel[{extnames}]', tuple(bases), _class_ns)

    def make_panel(self, panel_class, panel, attrs):
        """Create a panel object.  process_panel() calls this method."""
        # Required field
        # --------------
        # Date
        try:
            date_str = panel.pop('date')
        except KeyError:
            raise LoadError('panel must provide date') from None
        _assert_type(date_str, str, 'date')
        date = self.parse_date(date_str)
        obj = panel_class(date)

        # Optional fields
        # ---------------
        # Time zone
        if 'tz' in panel:
            tz = panel.pop('tz')
            _assert_type(tz, str, 'tz', 'in panel')
            attrs = attrs.copy()
            attrs['tz'] = tz
        # Rating
        rating = panel.pop('rating', None)
        _assert_type_or_none(rating, str, 'rating')
        if rating is not None:
            obj.set_rating(rating)

        # Entries
        # -------
        entries = panel.pop('entries', [])

        if panel:
            # I know map(str, ...) is totally redundant, but debugging
            # would suck if some mysterious object mixed in causing this
            # line to fail...
            keys_str = ', '.join(sorted(map(str, panel.keys())))
            plural = '' if len(panel) == 1 else 's'
            self._warn(f'ignored panel key{plural}: {keys_str}',
                       LoadWarning)

        for entry_dict in entries:
            entry = self.process_entry(entry_dict.copy(), obj, attrs)
            obj.add_entry(entry)

        return obj

    def process_entry(self, entry, panel, attrs):
        """Process a JSON object representing an entry.

        Parameters
        ----------
        entry : dict
            The JSON object (dict) to be processed.  This is a shallow
            copy and can be mutated.

        panel : Panel
            The panel that this entry belongs to.  Will be used to make
            inferences from.

        attrs : dict
            Attributes such as the time zone and lookup paths.  This
            should NOT be mutated (otherwise subsequent calls to
            process_entry() may behave weirdly).

        Return
        ------
        An Entry object, or None for skipping this entry.

        Note
        ----
        If you're using an extension, then more often than not you would
        probably want to override make_entry(), since this directly calls
        that.

        In addition, if you want to extend the entry class, override
        `get_entry_extensions()` and append your Entry subclass to the
        list of extensions.  (See the bigentry and captions extensions
        for how I did it.)
        """
        extensions = self.get_entry_extensions(entry, panel, attrs)
        entry_class = self.make_entry_class(extensions)
        return self.make_entry(entry_class, entry, panel, attrs)

    def get_entry_extensions(self, entry, panel, attrs):
        """Get a list of `Entry` subclasses, with the first base class
        coming last in the list.
        """
        return []

    def make_entry_class(self, extensions):
        """Create an `Entry` class with the `extensions` list
        reversed as the bases.
        """
        if not extensions:
            return Entry
        bases = list(extensions)
        extnames = ', '.join(cls.get_extension_name() for cls in bases)
        bases.reverse()
        bases.append(Entry)
        return type(f'Entry[{extnames}]', tuple(bases), _class_ns)

    def make_entry(self, entry_class, entry, panel, attrs):
        """Create an entry object.  process_entry() calls this method
        after an entry class has been made.

        Parameters
        ----------
        entry_class : subclass of Entry
            The class to create the entry with.

        entry, panel, attrs
            The same arguments passed from self.process_entry().

        Return
        ------
        An entry object constructed from `entry_class`, or None
        for skipping this entry.
        """
        # Required fields
        # ---------------
        # Date time

        # First check for the time zone.  If the user never set any,
        # we'll just assume no time zone (tz = None)
        if 'tz' in entry:
            tz = entry.pop('tz')
            _assert_type(tz, str, 'tz', 'in entry')
        else:
            # this should be None for omitting this in top level
            # and panel level
            tz = attrs['tz']
        if tz is not None:
            tz = self.parse_timezone(tz)

        if 'fold' in entry:
            fold = entry.pop('fold')
            _assert_type_or_none(fold, int, 'fold', article='an')
        else:
            # None for not changing the fold attribute of the parsed
            # datetime
            fold = None

        if 'date-time' in entry:
            dt_str = entry.pop('date-time')
            _assert_type(dt_str, str, 'date-time')
            date_time = self.parse_datetime(dt_str, tzinfo=tz, fold=fold)
            if 'time' in entry:
                raise LoadError("exactly one of 'date-time' and 'time' "
                                "can be provided")
        elif 'time' in entry:
            time_str = entry.pop('time')
            _assert_type(time_str, str, 'time')
            if 'date' in entry:
                date_str = entry.pop('date')
                _assert_type(date_str, str, 'date')
                date = self.parse_date(date_str)
            else:
                date = panel.date
            time = self.parse_time(time_str, tzinfo=tz, fold=fold)
            date_time = datetime.datetime.combine(date, time)
        else:
            raise LoadError("entry must provide time, either through "
                            "the key 'time' or 'date-time'")

        # Make sure that the tzinfo is there and working!
        # (i.e. aware datetime)
        if date_time.tzinfo is None:
            raise LoadError('time zone is not provided')
        if date_time.tzinfo.utcoffset(date_time) is None:
            raise LoadError(f'{date_time.tzinfo!r} returns None for '
                            f'utcoffset()')

        # Insight (optional but we have to get the value here)
        insight = entry.pop('insight', False)
        _assert_type(insight, bool, 'insight')

        # Do not link to the panel yet (so that user can override this
        # method and return a None instead if an entry is not desired)
        obj = entry_class(date_time, insight)

        # Type and format
        im = self.get_inference_manager()
        if 'type-format' in entry:
            type_format = entry.pop('type-format')
            _assert_type(type_format, str, 'type-format')
            e_type, e_format = type_format.split('-', 1)
        else:
            if 'type' in entry:
                e_type = entry.pop('type')
                _assert_type(e_type, str, 'type')
                e_type = im.alias_check(e_type)
            else:
                e_type = None

            if 'format' in entry:
                e_format = entry.pop('format')
                _assert_type(e_format, str, 'format')
            else:
                e_format = None

        # Encoding
        if 'encoding' in entry:
            e_enc = entry.pop('encoding')
            _assert_type(e_enc, str, 'encoding')
        else:
            # None just means the encoding wasn't provided.
            e_enc = None

        # Data and input
        if 'data' in entry and 'input' in entry:
            raise LoadError("only one of 'data' and 'input' can be "
                            "specified")
        if not ('data' in entry or 'input' in entry):
            raise LoadError("at least one of 'data' and 'input' "
                            "should be specified")

        # Process 'data' or 'input'
        #
        # The algorithm for inference is still very akin to basicproc.py
        # Check out 0.md (zero.rst in this repo) if you wanna see how that
        # works (i spent quite a lot of effort on it ;-;)
        if 'data' in entry:
            data = entry.pop('data')
            data = _ensure_text(data, 'data')
            if 'data-encoding' in entry:
                data_enc = entry.pop('data-encoding')
                _assert_type(data_enc, str, 'data-encoding')
                try:
                    func = self.get_option('data_decoders')[data_enc]
                except KeyError:
                    raise LoadError(f'invalid data encoding: '
                                    f'{data_enc!r}') from None
                raw = func(data)
                if e_type is None:
                    e_type = im.infer_type_from_encoding(e_enc)
                    if e_type is None:
                        e_type = 'binary'
                if e_enc is None:
                    e_enc = im.infer_encoding_from_type(e_type)
                    if e_enc is None:
                        e_enc = 'binary'
            else:
                # Python 3 strings are always Unicode.
                if not (e_enc is None or e_enc == 'utf-8'):
                    self._warn(f"'data': encoding {e_enc!r} treated as "
                               f"'utf-8'", LoadWarning)
                e_enc = 'utf-8'
                if e_type is None:
                    # This returns 'plain' precisely for our default
                    # implementation, but users may override this for
                    # a different default type.
                    e_type = im.infer_type_from_encoding(e_enc)
                    if e_type is None:
                        e_type = 'plain'
                raw = data.encode(e_enc)
            obj.set_raw_data(raw)
        else:
            path = entry.pop('input')
            _assert_type(path, str, 'input')
            obj.set_source(self.__find_path(path, attrs['paths']))
            if e_type is None:
                e_type = im.infer_type_from_path(path)
                if e_type is None:
                    e_type = im.infer_type_from_encoding(e_enc)
                    if e_type is None:
                        e_type = 'binary'
            if e_enc is None:
                e_enc = im.infer_encoding_from_type(e_type)
                if e_enc is None:
                    e_enc = 'binary'

        obj.set_type(e_type)
        obj.set_format(e_format)
        obj.set_encoding(e_enc)

        # Optional fields
        # ---------------
        # Question
        if 'question' in entry:
            question = entry.pop('question')
            _assert_type(question, str, 'question')
            obj.set_question(question)

        if entry:
            keys_str = ', '.join(sorted(map(str, entry.keys())))
            plural = '' if len(entry) == 1 else 's'
            self._warn(f'ignored entry key{plural}: {keys_str}',
                       LoadWarning)

        return obj

    def __find_path(self, path, paths):
        """Find an 'input' path with each directory path pattern in
        'paths' prepended to it.
        """
        base_dir = self.get_option('base_dir')
        if base_dir is None:
            raise LoadError('base_dir must be set when there are input paths')
        finder = find_paths(path, base_dir, paths)

        try:
            first = next(finder)
        except StopIteration:
            raise LoadError(f'cannot find path {path!r} (using '
                            f'base_dir = {base_dir!r})') from None

        # From the for loop above, since having warn_ambiguous_paths = False
        # would break the loop after the first match, it would imply that
        # matches more than 1 means that duplicates are found.
        if self.get_option('warn_ambiguous_paths'):
            try:
                next(finder)
            except StopIteration:
                pass
            else:
                self._warn(f'found more than one path for {path!r}; '
                           f'using the first path found {first!r} '
                           f'(base_dir = {base_dir!r})', LoadWarning)
        return first

    # These are simply convenient checking that I just like to keep here XD
    # These are private simply because I don't see any point in subclassing
    # these... (although a `check_hook` could be called every time a panel
    # is added... but again I don't see the point.  Yet.)
    def __check_panel_order(self, panels, index):
        if len(panels) < 2:
            return
        # The deque has a maximum of 2 items, so just unpact it
        panel_1, panel_2 = panels
        index_1, index_2 = index - 1, index
        if panel_1.date > panel_2.date:
            self._warn('panel #{} ({}) is after panel #{} ({})'
                       .format(index_1, panel_1.date, index_2, panel_2.date),
                       LoadWarning)
        if panel_1.date == panel_2.date:
            self._warn('panel #{} has the same date as #{} ({})'
                       .format(index_1, index_2, panel_2.date),
                       LoadWarning)

    def __check_entry_order(self, panel, p_index):
        # Stolen from basicproc.py
        has_switched = False
        expected_insight = None
        last_main_entry = None
        last_insight_entry = None
        # We have plenty of space so I changed i to index
        for index, entry in enumerate(panel.entries(), start=1):
            if expected_insight is None:
                expected_insight = entry.insight

            # Checking main -> insight order
            if expected_insight != entry.insight:
                if has_switched:
                    expected = ('an insight entry' if expected_insight
                                else 'a main entry')
                    got = ('an insight entry' if entry.insight
                           else 'a main entry')
                    msg = (f'expected entry {index} to be {expected}, got '
                           f'{got} (in panel {p_index} on {panel.date})')
                    self._warn(msg, LoadWarning)
                else:
                    has_switched = True
                    expected_insight = entry.insight

            # Checking main entry order
            if last_main_entry is not None and not entry.insight:
                if last_main_entry.time > entry.time:
                    msg = (f'inconsistent order in main entries in panel '
                           f'{p_index} on {panel.date} (entry {index} '
                           f'precedes entry {index - 1} in time)')
                    self._warn(msg, LoadWarning)

            # Checking insight entry order
            if last_insight_entry is not None and entry.insight:
                if last_insight_entry.time > entry.time:
                    msg = (f'inconsistent order in insight entries in panel '
                           f'{p_index} on {panel.date} (entry {index} '
                           f'precedes entry {index - 1} in time)')
                    self._warn(msg, LoadWarning)

            if entry.insight:
                last_insight_entry = entry
            else:
                last_main_entry = entry

    # Method hooks
    def parse_timezone(self, s):
        """Parse the 'tz' field."""
        return timeutil.parse_timezone(s)

    def parse_date(self, s):
        """Parse the 'date' field."""
        return timeutil.parse_date(s)

    def parse_datetime(self, s, tzinfo, fold):
        """Parse the 'date-time' field.  The tzinfo and fold arguments
        are None unless they are known.

        NOTE: When subclassing this, fold should be ignored when
        tzinfo is None.
        """
        return timeutil.parse_datetime(s, tzinfo=tzinfo, fold=fold)

    def parse_time(self, s, tzinfo, fold):
        """Parse the 'time' field, similar to parse_datetime().

        NOTE: When subclassing this, fold should be ignored when
        tzinfo is None.
        """
        return timeutil.parse_time(s, tzinfo=tzinfo, fold=fold)


# this was a method in JSONLoader exclusively until it becomes too
# important it has to be shared across two classes
#
# (it's also a generator now YIPPEE o_o)
def find_paths(path, base_dir, paths):
    """Yield all reachable file paths with the input path 'path'.

    get_lookup_paths() is called to obtain true lookup paths, and
    each lookup path is joined with 'path' to create a candidate path.
    If the candidate path exists, yield it.

    Arguments
    ---------
    path : str
        Input path.

    base_dir : str
        Absolute path to the base directory.

    paths : list of str
        Lookup paths.  Can include non-recursive Unix glob patterns.

    Yield
    -----
    Absolute (but not resolved), normalized file paths of the existing
    candidate paths.
    """
    for dirpath in get_lookup_paths(base_dir, paths):
        filepath = os.path.join(dirpath, path)
        if os.path.isfile(filepath):
            yield os.path.normpath(filepath)


def get_lookup_paths(base_dir, paths):
    """Yield existing directories determined by 'paths'.
    Helper generator of find_paths().

    Arguments
    ---------
    base_dir : str
        Absolute path to the base directory.

    paths : list of str
        Lookup paths.  Can include non-recursive Unix glob patterns.

    Yield
    -----
    Absolute (but not resolved), normalized lookup paths.
    """
    seen = set()
    for pattern in paths:
        # Append os.sep to ensure glob looks for directories only
        pattern = os.path.abspath(os.path.join(base_dir, pattern)) + os.sep
        for dirpath in glob.iglob(pattern):
            dirpath = os.path.normpath(dirpath)
            if not dirpath in seen:
                yield dirpath
                seen.add(dirpath)


# Below are implementation details!
def _can_find_any_other_path(target, prefix, base_dir, paths):
    """return whether any path can be found, ignoring extensions

    this is like saying next(find_paths(name, base_dir, paths), None)
    is not None, except any extension is permitted
    """
    dirname, prefix = os.path.split(prefix)
    target = os.path.realpath(target)
    n = len(prefix)
    for dirpath in get_lookup_paths(base_dir, paths):
        dirpath = os.path.join(dirpath, dirname)
        if os.path.exists(dirpath):
            # don't ask me python 3.6 told us to explicitly
            # close scandir iterators (shrug)
            # https://docs.python.org/3/whatsnew/3.6.html#os
            with os.scandir(dirpath) as scanner:
                for entry in scanner:
                    if (entry.name.startswith(prefix)
                            and entry.name[n:n+1] == '.'
                            and os.path.realpath(entry) != target):
                        return True
    return False


def _split_path(path):
    """splitting a relative path --- emphasis on RELATIVE!!!
    this won't work on an ABSOLUTE path because in that case
    'root' would never be empty
    """
    root = os.path.normpath(path)
    if root == '.':
        return []
    parts = []
    while root:
        root, name = os.path.split(root)
        parts.append(name)
        if not root:
            break
    parts.reverse()
    return parts


def _fn_pattern_match(path, pattern):
    """component-wise comparison using fnmatch"""
    file_parts = _split_path(path)
    pattern_parts = _split_path(pattern)
    if len(file_parts) != len(pattern_parts):
        return False
    for s, p in zip(file_parts, pattern_parts):
        if not fnmatch.fnmatch(s, p):
            return False
    return True


def _check_relpath(path, base_dir, name):
    """make sure that path is a relative path and join(base_dir, path)
    is inside base_dir.  if any of these conditions fails, DumpError.
    """
    if os.path.isabs(path):
        raise DumpError(f'{name}: {path!r} is absolute')
    abspath = os.path.abspath(os.path.join(base_dir, path))
    # i don't know if this rule makes sense but you shouldn't
    # really do this anyways so ummmm whatever
    # https://stackoverflow.com/a/37095733
    if (os.path.commonpath([abspath, base_dir])
            != os.path.commonpath([base_dir])):
        raise DumpError(f'{name}: {path!r} beyond base directory')


class JSONDumper(Configurable):
    """A JSON archive dumper.

    IMPORTANT NOTE: The default base directory is '.' which is almost
    NEVER what you want.  (Your files won't be overridden but it would
    be annoying if you have an existing directory named 'assets/'.)
    Remember to change it!!

    The constructor takes no positional arguments; all keyword
    arguments are passed to the `configure()` method.
    """
    __slots__ = ('_inference_manager',)

    def __init__(self, **kwargs):
        super().__init__()
        self.configure(**kwargs)

    def get_inference_manager(self):
        """Get the inference manager for this dumper."""
        try:
            return self._inference_manager
        except AttributeError:
            self._inference_manager = InferenceManager()
            return self._inference_manager

    def set_inference_manager(self, manager, /):
        """Set the inference manager for this dumper."""
        self._inference_manager = manager

    def _warn(self, msg, w):
        """Raise an exception with w(msg) if the `error_on_warning` option
        is set to True, else issue an warning.

        The `suppress_warnings` option overrides everything.
        """
        if self.get_option('suppress_warnings'):
            return
        if self.get_option('error_on_warning'):
            raise w(msg)
        import warnings
        warnings.warn(msg, w, 2)

    def dump(self, panels, fp, *, attrs=None):
        """Dump an iterable of panels to a file object.

        Arguments
        ---------
        panels : iterable of Panel objects
            The panels to dump.

        fp : file object
            A file-like object implementing the `write()` method.
            (Should be open in text mode)

        attrs : optional, mapping object
            Extra JSON top-level attributes to add after those
            created by prepare_backup().
        """
        data = self.dump_data(panels, attrs=attrs)
        self.dump_json(data, fp)

    def dump_json(self, data, fp):
        """Dump a dict as a JSON object to a file object.
        dump() calls this after constructing a dict with dump_data().

        Arguments
        ---------
        data : dict
            The dict to dump.

        fp : file object
            A file-like object implementing the `write()` method.
        """
        json.dump(data, fp, **self.get_option('json_options'))

    def dump_data(self, panels, *, attrs=None):
        """Dump an iterable of panels to a dict.  dump() calls this.
        For info on the arguments, see dump().
        """
        py_attrs = self.get_top_level_attributes(panels)
        data = dict(attrs) if attrs is not None else {}
        self.prepare_backup(data, py_attrs)
        if attrs is not None:
            data.update(attrs)
        panel_list = data['data'] = []
        for panel in panels:
            panel_dict = self.wrap_panel(panel, py_attrs)
            panel_list.append(panel_dict)
        if not panel_list:
            del data['data']
        return data

    # This panels attribute is INTENTIONALLY unused --- read
    # docstring or dumpy again for why
    def get_top_level_attributes(self, panels):
        """Get the top-level attributes for the iterable of panels.
        dump_data() calls this with its only argument.

        NOTE: The iterable of panels is directly passed from dump_data(),
        meaning if it is an iterator it will be exhausted by the time
        dump_data() gets to it.  Default implementation doesn't use this
        argument at all but be noted that you should convert it to a list
        if your subclass implementation uses it.
        """
        return {'tz': self.get_option('time_zone'),
                'paths': self.get_option('paths')}

    def prepare_backup(self, json_attrs, attrs):
        """Update the JSON top-level attributes from the top-level
        attributes.

        (Keep in mind that the 'data' key will always be overridden
        by dump_data() with the list of panels!)
        """
        tz = attrs['tz']
        if tz is not None:
            json_attrs['tz'] = self.format_timezone(tz)
        paths = attrs['paths']
        if paths != ['.']:
            json_attrs['paths'] = paths

    def wrap_panel(self, panel, attrs):
        """Convert a panel object into a dict.

        Arguments
        ---------
        panel : Panel object
            The panel to convert.

        attrs : dict
            Top-level attributes.

        Return
        ------
        A JSON-serializable dict representation of the panel.
        """
        if not isinstance(panel, Panel):
            raise TypeError(f'wrap_panel() expected a Panel object, '
                            f'got {panel!r}')
        panel_dict = {}
        panel_dict['date'] = self.format_date(panel.date)
        if panel.has_rating():
            panel_dict['rating'] = panel.get_rating()
        if panel.has_entries():
            entry_list = panel_dict['entries'] = []
            for entry in panel.entries():
                entry_dict = self.wrap_entry(entry, attrs)
                entry_list.append(entry_dict)
        return panel_dict

    # just like how process_entry() can be called independently
    # without panel linkage, we should be able to call wrap_entry()
    # with an unlinked entry too!
    def wrap_entry(self, entry, attrs):
        """Convert an entry object into a dict.

        Arguments
        ---------
        entry : Entry object
            The entry to convert.

        attrs : dict
            Top-level attributes.

        Return
        ------
        A JSON-serializable dict representation of the entry.
        """
        if not isinstance(entry, Entry):
            raise TypeError(f'wrap_entry() expected an Entry object, '
                            f'got {entry!r}')
        entry_dict = {}
        # time
        entry_time = entry.time
        tz = attrs['tz']
        if tz is not None:
            converted = entry_time.astimezone(tz)
            # we only require the utcoffset to be equal, as always?
            if converted.utcoffset() == entry_time.utcoffset():
                entry_time = entry_time.replace(tzinfo=None)
        if entry.has_panel() and entry.panel.date == entry_time.date():
            self.write_entry_time(entry_dict, entry_time)
        else:
            self.write_entry_date_and_time(entry_dict, entry_time)
        if entry.insight:
            entry_dict['insight'] = True
        # data and input
        base_dir = self.get_option('base_dir')
        paths = attrs['paths']
        input_path = self.get_input_path(entry, attrs)
        if input_path is None:
            self.__write_entry_data(entry_dict, entry)
        else:
            if not isinstance(input_path, str):
                raise TypeError(f'input path should be a str, not '
                                f'{input_path!r}')
            # ensure the input path get_input_path() gave was ok
            candidates = find_paths(input_path, base_dir, paths)
            try:
                first = next(candidates)
            except StopIteration:
                raise DumpError(f'unreachable input path '
                                f'{input_path!r}') from None
            try:
                next(candidates)
            except StopIteration:
                pass
            else:
                self._warn(f'more than one path found for input '
                           f'path {input_path!r}', DumpWarning)
            with (open(first, 'rb') as fp1,
                    entry.stream_raw_data() as fp2):
                if not util.fileobjequal(fp1, fp2):
                    raise DumpError(
                        f'entry raw data differs from the content '
                        f'of {first!r} (from the input path '
                        f'{input_path!r})')
            self.__write_entry_input(entry_dict, entry, input_path)
        # extra attributes (just question)
        if entry.has_question():
            entry_dict['question'] = entry.get_question()
        return entry_dict

    def get_input_path(self, entry, attrs):
        """Get an input path for the entry.  The arguments passed are
        the exact same from wrap_entry().  This determines whether an entry
        is exported or kept inside the backup dict.

        Arguments
        ---------
        entry, attrs
            See wrap_entry().

        Return
        ------
        None is returned when an entry is to be kept inside the backup dict.
        Otherwise, a str is returned.

        Several notes on the implementation:

          *  get_input_path() should create the appropriate file it is
             referring to and it is valid as long as its content matches
             that of entry.get_raw_data().

          *  It is unnecessary to raise any exceptions when get_input_path()
             fails to generate an input path.  Just return an arbitrary
             string and let wrap_entry() do its job.

          *  (JSONDumper) When overriding this method, feel free to just
             copy and modify the default implementation!  The 'assets'
             variable is hard-coded just for that reason ;)
        """
        # by default we don't keep entries that don't have
        # a sufficient text representation.
        if self.use_inline_text(entry):
            return None
        # always export to the 'assets' directory; this is hard-coded
        dirname = 'assets'
        base, ext = self.get_export_path_name(entry)
        paths = attrs['paths']
        # this is like 'base + ext' but safer (and fancier)
        filename = self.generate_export_path(entry, base, ext,
                                             dirname, paths)
        self.export_entry(entry, os.path.join('assets', filename))
        # arbitrarily extend the input path by its directory name
        return self.compute_input_path(filename, 'assets', paths)

    def get_export_path_name(self, entry):
        """Return (base, ext) for the export file name of an entry."""
        etime = entry.time.replace(tzinfo=None)
        name = etime.isoformat('_').replace(':', '-')
        # prepend the panel's date only if entry has a panel whose date
        # differs from its time
        if entry.has_panel() and etime.date() != entry.panel.date:
            name = f'{entry.panel.date}_{name}'
        ctx = filetypes.get_context()
        try:
            return name, ctx.get_default_extension(entry.get_type())
        except LookupError:
            return name, ''

    def get_export_path_candidates(self, name):
        """Return an iterator (infinite or finite, depending on what
        you want) of the base name (the part of file name excluding
        extension) for generate_export_path() to use.
        """
        # file names: 'name.txt', 'name_001.txt', 'name_002.txt', ...
        # (this doesn't return the '.txt' part, but you get the gist.)
        return itertools.chain(
            [name], (f'{name}_{i:03}' for i in itertools.count(1)))

    def generate_export_path(self, entry, base, ext, dirname, paths):
        """Generate a nonexistent, unambiguous file name for exporting.
        (Yes, the function name is a bit misleading, but it does not return
        an actual path.  Sorry but I couldn't think of a better name.)

        This docstring is meant to give a technical overview, so it might
        not be the best for those lacking the general background!
        (i'll write about it somewhere else yeah)

        Arguments
        ---------
        entry : Entry object
            The entry we want to export

        base : str
            The base name, or the part of file name without extension.
            This can contain more than one file component, but a DumpWarning
            will be issued if there is the POTENTIAL of making existing input
            paths ambiguous as this is taken to be the shortest permitted
            input path.

        ext : str
            The file extension.  Should just be the extension and nothing
            else. (like don't write '.txt/../somewhere_else.txt' it's not
            gonna work lol)

        dirname : str
            The directory path.  A relative directory path such that
            join(dirname, base + ext) where join = os.path.join is a
            valid path.

        paths : list of str
            The 'paths' attribute.

        Return
        ------
        The first nonexistent, unambiguous file name.  File extensions are
        disregarded, so 'name.txt' is considered to be the same file as
        'name.pdf' or 'name.tar.gz'.

        The file base name is acquired from get_export_path_candidates().
        A DumpError is raised if the iteration of get_export_path_candidates()
        ended before a successful file name is returned.
        """
        base_dir = self.get_option('base_dir')
        try:
            base_dir = os.fspath(base_dir)
        except TypeError:
            msg = 'base_dir must be set when calling generate_export_path()'
            raise DumpError(msg) from None
        # just to check if the extension contains any slashes
        ext_head, ext_tail = os.path.split(ext)
        if ext_head or ext_tail != ext:
            raise ValueError(f'invalid file extension: {ext!r}')
        abs_dirname = os.path.normpath(os.path.join(base_dir, dirname))

        # since the file name ('base' and 'ext' considered as a whole) can be
        # arbitrarily extended by 'dirname', we also have to make sure the
        # numbering doesn't collide with them
        dirparts = _split_path(dirname)
        # prefixes starts with no prefix, then includes directories
        # one by one from right to left... (i = n-1, n-2, ... 1, 0)
        prefixes = [os.path.join(*dirparts[i:] or ['']) for i in
                    reversed(range(len(dirparts) + 1))]

        # make sure the file name 'name' is the shortest reachable path to
        # 'join(dirname, name)', otherwise issue a warning (one is enough)
        parts = _split_path(base)
        # for a 'name' that looks like 'a/b/.../c/d/name', iterate through
        # directives 'a', 'a/b', ..., 'a/b/.../c', 'a/b/.../c/d' and warn
        # the user if any of the above matches a pattern in 'paths'
        for i in range(1, len(parts)):
            long_dir = os.path.normpath(os.path.join(dirname, *parts[:i]))
            for lookup_path in paths:
                if _fn_pattern_match(long_dir, lookup_path):
                    name = f'{base}{ext}'
                    export_path = (
                        os.path.normpath(os.path.join(dirname, name)))
                    self._warn(
                        f'{name!r} is not the shortest reachable '
                        f'path for {export_path!r} (parent directory '
                        f'{os.path.join(*parts[:i])!r} matches the lookup '
                        f'path {lookup_path!r}); name collisions may occur',
                        DumpWarning)
                    break
            # break the outer loop when the inner loop is broken:
            # one warning is enough
            else:
                continue
            break

        for candidate in self.get_export_path_candidates(base):
            # test if the path being exported to is OK
            filename = f'{candidate}{ext}'
            export_path = os.path.join(abs_dirname, filename)
            if not self.export_path_ok(export_path, entry):
                continue
            # test if the path with the current numbering matches against
            # none of the existing files.  if any path, with any arbitrarily
            # extended prefix, matched at all, we start over.
            matched = False
            for prefix in prefixes:
                extended = os.path.join(prefix, candidate)
                if _can_find_any_other_path(
                        export_path, extended, base_dir, paths):
                    matched = True
                    break
            if not matched:
                return filename

        # we've tried everything so just give up (lol you can count on
        # me for optimism)
        name = f'{base}{ext}'
        raise DumpError(f'failed to generate a file name for {name!r} '
                        f'(with directory name {dirname!r})')

    def export_path_ok(self, export_path, entry):
        """Return whether the file at export_path represents the
        raw data in the entry correctly"""
        if os.path.exists(export_path):
            with open(export_path, 'rb') as fp:
                with entry.stream_raw_data() as fpref:
                    return util.fileobjequal(fp, fpref)
        return True

    def compute_input_path(self, name, dirname, paths):
        """Compute a (potentially) valid input path.
        Note that join(dirname, name) has to exist for this to work!

        Arguments
        ---------
        name : str
            The file name.  Will be used as the shortest input path.

        dirname : str
            The directory path relative to paths.  Will be used to
            progressively extend 'name'.

        paths : list of str
            The 'paths' attribute.

        Return
        ------
        The shorest unambiguous path, or the full path if all fails.

        Note
        ----
        This function makes no guarantee that an input path will remain
        unambiguous in the future (see what I wrote in dumpy log).
        It's at your own risk if you don't use generate_export_path() or
        use inconsistent lookup paths!
        """
        base_dir = self.get_option('base_dir')
        try:
            base_dir = os.fspath(base_dir)
        except TypeError:
            msg = 'base_dir must be set when calling compute_input_path()'
            raise DumpError(msg) from None
        parts = _split_path(dirname)
        name = input_path = os.path.normpath(name)
        target = os.path.abspath(os.path.join(base_dir, dirname, name))
        # the one and only path we should find must be 'target'
        # otherwise the loop continues until we obtain the full path
        while True:
            finder = find_paths(input_path, base_dir, paths)
            try:
                first = next(finder)
            except StopIteration:
                pass
            else:
                if os.path.samefile(target, first):
                    try:
                        next(finder)
                    except StopIteration:
                        break
            try:
                input_path = os.path.join(parts.pop(), input_path)
            except IndexError:
                break
        return input_path

    def export_entry(self, entry, export_path):
        """Export entry to an export path.  The export path is relative
        to the base_dir option.  Intermediary directies are created
        with os.makedirs() even if they exist, although the export path
        must not exist by the time of being exported.

        CHANGE: I uhhh made this a no-op when export_path exists
        (namely when generate_export_path() returns an existing path)
        The rationale here is that we make this function simply ENSURE
        that a path is created, if it exists and has mismatching content
        wrap_entry() would complain anyways
        """
        base_dir = os.path.abspath(self.get_option('base_dir'))
        # convert base_dir to an absolute path for the following
        # commonpath() check to work
        try:
            base_dir = os.path.abspath(base_dir)
        except TypeError:
            msg = 'base_dir must be set when calling export_entry()'
            raise DumpError(msg) from None
        _check_relpath(export_path, base_dir, 'export_path()')
        export_path = os.path.join(base_dir, export_path)
        if not os.path.exists(export_path):
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with entry.stream_raw_data() as fsrc:
                with open(export_path, 'xb') as fdst:
                    shutil.copyfileobj(fsrc, fdst)

    def __write_entry_data(self, entry_dict, entry):
        """branch of wrap_entry() for inline data"""
        im = self.get_inference_manager()
        e_type = entry.get_type()
        e_enc = entry.get_encoding()
        e_format = entry.get_format()
        if self.use_inline_text(entry):
            # encoding is always 'utf-8' so we don't need to put
            # that in.  Provide 'type' only if type can't be correctly
            # inferred from encoding.
            i_type = im.infer_type_from_encoding('utf-8')
            if i_type is None:
                i_type = 'plain'
            if i_type != e_type:
                self.write_entry_type_and_format(entry_dict, e_type, e_format)
            elif e_format is not None:
                entry_dict['format'] = e_format
            self.write_entry_text_data(entry_dict, entry)
        else:
            self.__write_binary_entry(entry_dict, e_type, e_enc, e_format)
            self.write_entry_binary_data(entry_dict, entry)

    def __write_entry_input(self, entry_dict, entry, input_path):
        """branch of wrap_entry() for exporting"""
        im = self.get_inference_manager()
        e_type = entry.get_type()
        e_enc = entry.get_encoding()
        e_format = entry.get_format()
        # note that once type is successfully inferred from the
        # input path, encoding will NOT be used to infer again
        i_type = im.infer_type_from_path(input_path)
        if i_type is not None:
            if i_type != e_type:
                self.write_entry_type_and_format(entry_dict, e_type, e_format)
            elif e_format is not None:
                entry_dict['format'] = e_format
            i_enc = im.infer_encoding_from_type(e_type)
            if i_enc is None:
                i_enc = 'binary'
            if i_enc != e_enc:
                entry_dict['encoding'] = e_enc
        else:
            # fallback to the same reverse inference rules as inline
            # binary data
            self.__write_binary_entry(entry_dict, e_type, e_enc, e_format)
        entry_dict['input'] = input_path

    # the same code twice so i don't have to copy-and-paste
    def __write_binary_entry(self, entry_dict, e_type, e_enc, e_format):
        """common reverse inference rules for inline binary & exported
        entries when type cannot be inferred from input path
        """
        im = self.get_inference_manager()
        # if type can be inferred from the LACK of encoding
        # and encoding can THEN be inferred from that type,
        # no information is needed.
        i_type = im.infer_type_from_encoding(None)
        if i_type is None:
            i_type = 'binary'
        i_enc = im.infer_encoding_from_type(e_type)
        if i_enc is None:
            i_enc = 'binary'
        if i_type == e_type and i_enc == e_enc:
            if e_format is not None:
                entry_dict['format'] = e_format
        else:
            # if type can be inferred from encoding, then just
            # encoding is enough.  otherwise type must be provided.
            i_type = im.infer_type_from_encoding(e_enc)
            if i_type is None:
                i_type = 'binary'
            if i_type == e_type:
                entry_dict['encoding'] = e_enc
                if e_format is not None:
                    entry_dict['format'] = e_format
            else:
                self.write_entry_type_and_format(entry_dict, e_type, e_format)
                # provide encoding only if it can't be correctly
                # inferred from type
                if i_enc != e_enc:
                    entry_dict['encoding'] = e_enc

    def format_timezone(self, tz):
        """Format a tzinfo object as a str."""
        # users can allow more interesting input (ANSI time zone
        # with zoneinfo, for instance), but only with the appropriate
        # extension of parse_timezone()
        if isinstance(tz, datetime.timezone):
            if tz is datetime.timezone.utc:
                return 'UTC'
            # since datetime.timezone is a fixed offset, just pass any
            # arbitrary datetime and we should be good
            return timeutil.format_offset(
                tz.utcoffset(datetime.datetime.min))
        raise ValueError(f'cannot serialize time zone {tz!r}')

    def format_date(self, date):
        """Format a date object as a str."""
        return timeutil.format_date(date)

    def write_entry_time(self, entry_dict, dt):
        """Update entry_dict with entry time, omitting the date."""
        entry_dict['time'] = self.format_time(dt)
        # In case that dt is naive and the time zone is inherited from the
        # top-level attribute tz, make sure that we also serialize the fold
        # attribute.  We don't have to worry about the case where dt is
        # aware as format_time() always uses a fixed offset.
        if timeutil.is_naive(dt) and dt.fold:
            entry_dict['fold'] = dt.fold

    def write_entry_date_and_time(self, entry_dict, dt):
        """Update entry_dict with entry time, including the date."""
        entry_dict['date-time'] = self.format_datetime(dt)
        if timeutil.is_naive(dt) and dt.fold:
            entry_dict['fold'] = dt.fold

    # XXX: experimental? don't use these yet???
    def format_time(self, dt):
        """Format an aware/naive datetime object as a time str."""
        return timeutil.format_time(dt)

    def format_datetime(self, dt):
        """Format an aware/naive datetime object as a datetime str."""
        return timeutil.format_datetime(dt)

    def write_entry_type_and_format(self, entry_dict, e_type, e_format):
        """Update entry_dict with entry type and format."""
        if '-' not in e_type and e_format is not None:
            entry_dict['type-format'] = f'{e_type}-{e_format}'
        else:
            entry_dict['type'] = e_type
            if e_format is not None:
                entry_dict['format'] = e_format

    def use_inline_text(self, entry):
        """Return whether an entry can and will be fully represented with
        inline text.  Every entry can be represented as inline binary, but
        not every entry can be represented as inline text.  This method is
        ONLY called when an entry is NOT being exported.
        """
        return entry.is_text()

    # technically this doesn't have to be a method updating entry_dict,
    # but meh, i'll keep it consistent even if it's just one attribute.
    def write_entry_text_data(self, entry_dict, entry):
        """Update entry_dict with inline text representation of entry.
        This usually means assigning a str to the 'data' key.

        Note: DO NOT write type, encoding, or format as that is already
        done for you!
        """
        entry_dict['data'] = entry.get_data()

    def write_entry_binary_data(self, entry_dict, entry):
        """Update entry_dict with inline binary representation of entry.
        This usually means assigning an encoded str to the 'data' key
        and adding the appropriate data encoding.

        Note: DO NOT write type, encoding, or format as that is already
        done for you!
        """
        data_enc, data = self.get_option('data_encoder')(entry)
        entry_dict['data'] = data
        entry_dict['data-encoding'] = data_enc


# Options
# -------
data_decoders = {
    'base16': base64.b16decode,
    'base32': base64.b32decode,
    'base64': base64.b64decode,
    'base64_url': base64.urlsafe_b64decode,
    'ascii85': base64.a85decode,
    'base85': base64.b85decode,
}


def data_encoder(entry):
    return 'base64', base64.b64encode(entry.get_raw_data()).decode('ascii')


def type_checker(cls):
    def checker(_self, name, value):
        if not isinstance(value, cls):
            raise TypeError(f'the {name!r} option should be an instance of '
                            f'{cls.__qualname__!r}, not {value!r}')
        return value
    return checker


def type_checker_ii(cls):
    def checker(_self, name, value):
        if not (value is None or isinstance(value, cls)):
            raise TypeError(f'the {name!r} option should be an instance of '
                            f'{cls.__qualname__!r} or None, not {value!r}')
        return value
    return checker


bool_checker = type_checker(bool)
list_checker = type_checker(list)
dict_checker = type_checker(dict)


def callable_checker(_self, _name, value):
    if not callable(value):
        raise TypeError(f'the {name!r} option should be a callable, not '
                        f'{value!r}')
    return value


def base_dir_checker(_self, _name, value):
    if not (value is None or isinstance(value, (str, os.PathLike))):
        raise TypeError(f"the 'base_dir' option should be None, a str, or "
                        f"a path-like object, not {value!r}")
    return value


def make_paths_checker(list_checker):
    def paths_checker(self, name, value):
        list_checker(self, name, value)
        paths = []
        for i, item in enumerate(value, start=1):
            if not isinstance(item, (str, os.PathLike)):
                raise TypeError(f"expected item {i} of the 'paths' option "
                                f"to be a str or path-like object, got {item!r}")
            paths.append(os.fspath(item))
        return paths
    return paths_checker

paths_checker = make_paths_checker(list_checker)
del make_paths_checker


JSONLoader.add_option('base_dir', None, base_dir_checker)
JSONLoader.add_option('json_options', {}, dict_checker)
JSONLoader.add_option('check_panel_order', True, bool_checker)
JSONLoader.add_option('check_entry_order', True, bool_checker)
# When check_panel_order is disabled, one may enable this to
# merely check for duplicate panels
JSONLoader.add_option('suppress_warnings', False, bool_checker)
JSONLoader.add_option('error_on_warning', False, bool_checker)
JSONLoader.add_option('warn_ambiguous_paths', True, bool_checker)
JSONLoader.add_option('data_decoders', data_decoders, dict_checker)

JSONDumper.add_option('base_dir', None, base_dir_checker)
JSONDumper.add_option('json_options', {}, dict_checker)
JSONDumper.add_option('data_encoder', data_encoder, callable_checker)
JSONDumper.add_option('paths', ['.'], paths_checker)
JSONDumper.add_option('time_zone', None, type_checker_ii(datetime.tzinfo))
JSONDumper.add_option('suppress_warnings', False, bool_checker)
JSONDumper.add_option('error_on_warning', False, bool_checker)

del data_decoders, data_encoder
del type_checker, type_checker_ii, bool_checker, list_checker, dict_checker
del base_dir_checker, paths_checker, callable_checker


# TODO: address convenience interface of providing date
def load_json(file, date=None, *, encoding=None, errors=None,
              loader=None, **options):
    """Convenience interface for loading a JSON archive.

    NOTE: Extra keyword arguments are used only if a loader
    isn't provided.

    Arguments
    ---------
    file : path-like or readable text file-like object
        JSON archive file to read from.

    date : optional, datetime.date object or str
        When provided, return the first panel whose date equals
        this argument.  When omitted, return all panels.
        If date is a str, it is converted to a datetime.date
        with the parse_date() method of the loader.

    encoding, errors : str
        Optional arguments for the built-in open() function.

    loader : optional, JSONLoader instance
        The underlying loader object to use.  By default,
        a JSONLoader is created with the extra keyword arguments.
    """
    if isinstance(file, (str, os.PathLike)):
        options.setdefault('base_dir', os.path.dirname(file))
    if loader is None:
        loader = JSONLoader(**options)
    if hasattr(file, 'read'):
        fp = file
        close = False
    else:
        fp = io.open(file, encoding=encoding, errors=errors)
        close = True
    try:
        if date is not None:
            # convert date if it is a string
            if isinstance(date, str):
                date = loader.parse_date(date)
            elif not isinstance(date, datetime.date):
                raise TypeError(f'date should be a str or datetime.date, '
                                f'not {date!r}')
            # filter and return the first result
            try:
                return next(p for p in loader.load(fp) if p.date == date)
            except StopIteration:
                raise ValueError(f'date {date} not found') from None
        return list(loader.load(fp))
    finally:
        if close:
            fp.close()


def dump_json(panels, file, *, attrs=None, encoding=None, errors=None,
              exist_ok=False, dumper=None, **options):
    """Convenience interface for dumping a JSON archive.

    NOTE: Extra keyword arguments are used only if a dumper
    isn't provided.

    Arguments
    ---------
    file : path-like or writable text file-like object
        JSON archive file to dump to.

    attrs : optional, mapping object
        Addition JTL attributes passed to JSONDumper.dump().

    encoding, errors : optional, str
        Optional arguments for the built-in open() function.

    exist_ok : bool, default False
        (Only applicable when 'file' is a path-like object)
        If True, open in 'w' mode.  Otherwise open in 'x' mode.

    dumper : optional, JSONLoader instance
        The underlying doader object to use.  By default,
        a JSONDoader is created with the extra keyword arguments.
    """
    if isinstance(file, (str, os.PathLike)):
        options.setdefault('base_dir', os.path.dirname(file))
    if dumper is None:
        dumper = JSONDumper(**options)
    if hasattr(file, 'read'):
        fp = file
        close = False
    else:
        mode = 'w' if exist_ok else 'x'
        fp = io.open(file, mode, encoding=encoding, errors=errors)
        close = True
    try:
        dumper.dump(panels, fp)
    finally:
        if close:
            fp.close()
