"""Processor for JSON archives."""

import base64
import copy
import collections
import datetime
import fnmatch
import io
import itertools
import glob
import json
import os
import shutil

from ..types import Panel, Entry
from .. import datatypes
from .. import timeutil

__all__ = [
    'JSONLoader', 'JSONDumper',
    'LoadError', 'DumpError', 'LoadWarning',
    'load_json', 'dump_json',
]


class LoadError(Exception):
    """Error that occured while loading a JSON archive."""


class LoadWarning(UserWarning):
    """Warning that occured while loading a JSON archive."""


class DumpError(Exception):
    """Error that occured while dumping a JSON archive."""


def _assert_type(obj, objtype, key, extra=''):
    """Assert that `obj` has type `objtype`, else raise a TypeError
    exception.

    Parameter
    ---------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.
    """
    if isinstance(obj, objtype):
        return
    keyname = f'{key!r}{extra}'
    typename = objtype.__name__
    clsname = type(obj).__name__
    raise TypeError(f'{keyname}: expected a {typename}, '
                    f'got {clsname}')


def _assert_type_or_none(obj, objtype, key, extra=''):
    """Assert that `obj` has type `objtype` or is None (JSON null),
    else raise a TypeError exception.

    Parameters
    ----------
    key : str
        The name of the JSON key the attribute belongs to.
        This will be formatted in its repr form in the exception.

    extra : str, optional
        Extra string to append to the exception message.
        This will be appended after `key`.
    """
    if isinstance(obj, objtype) or obj is None:
        return
    keyname = f'{key!r}{extra}'
    typename = objtype.__name__
    clsname = type(obj).__name__
    raise TypeError(f'{keyname}: expected a {typename} or None, '
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
    for i, item in enumerate(obj):
        if isinstance(item, item_type):
            continue
        header = repr(key) if extra is None else f'{key!r}{extra}'
        typename = item_type.__name__
        clsname = type(obj).__name__
        raise TypeError(f'{header}: expected a list of {typename}, '
                        f'found item {i} to be a {clsname}')


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
    """
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        try:
            return ''.join(obj)
        except TypeError:
            # We already know there's something wrong in the list, so
            # let _assert_list_type() raise that error for us.
            _assert_list_type(obj, str, key, extra)
    header = f'{key!r}{extra}'
    clsname = type(obj).__name__
    raise TypeError(f'{header}: expected a str or a list of str, '
                    f'got {clsname!r}')


_data_enc_table = {
    'base16': base64.b16decode,
    'base32': base64.b32decode,
    'base64': base64.b64decode,
    'base64_url': base64.urlsafe_b64decode,
    'ascii85': base64.a85decode,
    'base85': base64.b85decode,
}


class JSONLoader:
    """A JSON archive loader.

    The constructor takes no positional arguments.  The keyword arguments
    are passed to the `configure` method.

    NOTE: Don't rely on tweaking the attributes of this class!
    Use the `configure` method when you need to change something, and in
    case you want to access an option... well don't.  They're not supposed
    to be public anyways.  :/
    """
    __slots__ = ('_all_options', '_options')

    def __init__(self, **options):
        # TODO: Write documentation for these options

        # Since you only need one or two loaders at a time, creating
        # a list of options shouldn't be a memory issue.
        #
        # This is to make subclassing possible, where options are
        # extended based on this.
        self._all_options = {
            # 'load_from_file', # 'validate',
            'check_panel_duplicates', 'check_panel_order',
            'check_entry_order', 'error_on_warning', 'suppress_warnings',
            'paths', 'base_dir', 'json_options', 'warn_ambiguous_paths',
        }

        self._options = {
            'check_panel_order': True,
            'check_entry_order': True,
            # When check_panel_order is disabled, one may enable this to
            # merely check for duplicate panels
            'check_panel_duplicates': False,
            'error_on_warning': False,
            'suppress_warnings': False,
            'warn_ambiguous_paths': True,

            # directories paths to prepend to input paths when they're not
            # found
            'paths': (),
            # the base directory, used as the ROOT of relative paths
            'base_dir': os.getcwd(),
            # keyword arguments to pass to json.loads
            'json_options': {},
        }
        self.configure(**options)

    def configure(self, **options):
        """Configure options.  This method should be called instead of
        directly accessing the underlying attributes.

        (i will write the options in a document one day, just you wait...)
        """
        invalid = options.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            plural = '' if len(invalid_str) == 1 else 's'
            raise ValueError(f'invalid key{plural}: {invalid_str}')
        for k, v in options.items():
            try:
                checker = getattr(self, f'check_{k}_option')
            except AttributeError:
                pass
            else:
                v = checker(v)
            self._options[k] = v

    def get_option(self, name):
        return self._options[name]

    def _warn(self, msg, w):
        """Raise an exception with w(msg) if the `error_on_warning` option
        is set to True, else issue an warning.

        The `suppress_warnings` option overrides everything.
        """
        if self.get_option('suppress_warnings'):
            return
        if self.get_option('error_on_warning'):
            raise w(msg)
        else:
            import warnings
            warnings.warn(msg, w, 2)

    def load(self, file, date=None, *, encoding='utf-8'):
        """Load an archive from a file as a list of `Panel`s.

        If `date` is provided, optimize the loading process by only
        returning the panel on that date.

        Parameters
        ----------
        file : path-like object or file-like object
            May be a file path to the JSON archive to be read (an instance
            of `str` or `os.PathLike`) or a readable file-like object
            (an object with a `read()` method that returns the file content
            as a `str`).

        date : datetime.date object or object, optional
            A `datetime.date` instance or a `str` representing a date.
            The string must be valid for `timeutil.parse_date`.

        encoding : str, default 'utf-8'
            The encoding used to open `file` if it is a file path.

        Return
        ------
        -   Return `panels` if `date` is not provided; and
        -   Return `panel` is `date` is provided.
        """
        content = self.__handle_readable_file(file, encoding)
        data = json.loads(content, **self.get_option('json_options'))
        return self.load_data(data, date)

    def __handle_readable_file(self, file, encoding):
        """Handle a path-like or file-like object and return the file
        content on success.
        """
        if isinstance(file, (str, os.PathLike)):
            with io.open(file, 'r', encoding=encoding) as fp:
                content = fp.read()
        elif hasattr(file, 'read'):
            content = file.read()
        else:
            raise TypeError(f'file should be a path-like object or a '
                            f'readable file-like object, not {file!r}')
        return content

    # TODO: CONTINUE WRITING DOCSTRINGS
    def load_data(self, data, date=None):
        panels, attrs = self.__split_data(data)
        if date is None:
            obj = self.__load_all_data(panels, attrs)
        else:
            if isinstance(date, str):
                date = timeutil.parse_date(date)
            elif not isinstance(date, datetime.date):
                raise TypeError(f'date should be a str or datetime.date '
                                f'object, not {type(date).__name__}')
            obj = self.__load_single_panel(panels, attrs, date)
        return obj

    def __split_data(self, data):
        # The name might be a bit misleading since it doesn't actually
        # simply "split" the data (since we're not returning the
        # attributes and so it remains a local variable to us).
        if not isinstance(data, dict):
            raise TypeError('JSON data should be a dictionary')
        data = data.copy()
        # This list is not safe to pop() (as it is a reference to the
        # original list)
        panels = data.pop('data', [])
        _assert_list_type(panels, dict, 'data')

        # The rest of 'data' are attributes.
        attrs = data

        if 'paths' in data:
            # Make a copy of 'paths' so as to not mutate the original list,
            # and at the same time reassign it to attrs.
            paths = attrs['paths']
            _assert_list_type(paths, str, 'paths')
            # Create a list from the lookup paths from the 'paths' option
            # and append the ones from attrs to it.
            combined = list(self.get_option('paths'))
            combined.extend(paths)
            attrs['paths'] = combined
        else:
            # Directly take the paths from the 'paths' option
            paths = list(self.get_option('paths'))
            # In case the option was empty, use ['.'].
            attrs['paths'] = paths or ['.']

        if 'tz' in attrs:
            _assert_type(attrs['tz'], str, 'tz', 'top level')

        return panels, attrs

    def __load_all_data(self, panels, attrs):
        output = []
        check_panel_order = self.get_option('check_panel_order')
        check_entry_order = self.get_option('check_entry_order')
        for panel_dict in panels:
            if not self.panel_filter(panel_dict):
                continue
            try:
                # Copy panel because we want the exception below to
                # be raised properly.
                # Copy attrs too because attrs can be assigned to a
                # new item like time zone.
                panel = self.process_panel(panel_dict.copy(), attrs.copy())
            except (TypeError, ValueError, LoadError, LoadWarning) as exc:
                # To make debugging life easier
                if 'date' in panel_dict:
                    raise LoadError(f'error while loading '
                                    f'{panel_dict["date"]}') from exc
                elif output:
                    raise LoadError(f'error after loading '
                                    f'{output[-1].date}') from exc
                raise

            if panel is not None:
                output.append(panel)

                if check_panel_order:
                    self.__check_panel_order(output)
                if check_entry_order:
                    self.__check_entry_order(panel)

        if not check_panel_order:
            if self.get_option('check_panel_duplicates'):
                self.__check_panel_duplicates(output)
        return output

    # Callback that can be overridden to load only certain panels
    # (this one skips empty JSON objects, so [ {}, null, '' ] are skipped)
    def panel_filter(self, panel_dict):
        return panel_dict

    def __load_single_panel(self, panels, attrs, date):
        # TODO: Implement check duplicate panels/panel order
        for panel_dict in panels:
            try:
                panel_date = self.parse_date(panel_dict['date'])
            except (KeyError, TypeError, ValueError):
                # XXX: Should errors be passed silently?
                continue
            if panel_date == date:
                break
        else:
            raise LookupError(f'cannot find panel with date {date}')

        panel = self.process_panel(panel_dict, attrs)
        if panel is not None and self.get_option('check_entry_order'):
            self.__check_entry_order(panel)
        return panel

    def process_panel(self, panel, attrs):
        """Process a JSON object of an Entry.

        Parameters
        ----------
        panel : dict
            The JSON object (dict) to be processed.

        attrs : dict
            Attributes such as the time zone and lookup paths.
        """
        # Required field
        # --------------
        # Date
        try:
            date_str = panel.pop('date')
        except KeyError:
            raise LoadError('panel must provide date')
        _assert_type(date_str, str, 'date')
        date = self.parse_date(date_str)
        obj = Panel(date)

        # Optional fields
        # ---------------
        # Time zone
        if 'tz' in panel:
            tz = panel.pop('tz')
            _assert_type(tz, str, 'tz', 'in panel')
            attrs['tz'] = tz
        # Rating
        rating = panel.pop('rating', None)
        _assert_type_or_none(rating, str, 'rating')
        obj.set_attribute('rating', rating)

        # Entries
        # -------
        entries = panel.pop('entries', [])

        if panel:
            keys_str = ', '.join(sorted(map(str, panel.keys())))
            plural = '' if len(panel) == 1 else 's'
            self._warn(f'ignored panel key{plural}: {keys_str}',
                       LoadWarning)

        for index, entry_dict in enumerate(entries, start=1):
            # 'attrs' is only accessed and not mutated, so no need to copy.
            # However we do need to copy the entry... because we only assumed
            # that whoever called process_panel() only made a shallow copy
            # of the 'panel' dictionary...
            if not self.entry_filter(entry_dict):
                continue
            try:
                entry = self.process_entry(obj, entry_dict.copy(), attrs)
            except (TypeError, ValueError, LoadError, LoadWarning) as exc:
                raise LoadError(
                    f'error while loading entry {index}') from exc
            obj.add_entry(entry)

        return obj

    def entry_filter(self, entry_dict):
        return entry_dict

    def process_entry(self, panel, entry, attrs):
        """Process a JSON object of an Entry.

        Parameters
        ----------
        panel : Panel
            The panel that this entry belongs to.  Will be used to make
            inferences from.

        entry : dict
            The JSON object (dict) to be processed.  This can be mutated.

        attrs : dict
            Attributes such as the time zone and lookup paths.  This
            should NOT be mutated.
        """
        # Required fields
        # ---------------
        # Date time

        # First check for the time zone.  If the user never set any, we'll
        # just assume no time zone (tz = None)
        if 'tz' in entry:
            tz = entry.pop('tz')
            _assert_type(tz, str, 'tz', 'in entry')
        elif 'tz' in attrs:
            tz = attrs['tz']
        else:
            # LoadError for the omitted time zone (as tz = None) will be
            # raise later when checking for the tzinfo of date_time.
            tz = None
        if tz is not None:
            tz = timeutil.parse_timezone(tz)

        if 'fold' in entry:
            fold = entry.pop('fold')
            _assert_type_or_none(fold, int, 'fold')
        else:
            # None for not changing the fold attribute of the parsed datetime
            fold = None

        if 'date-time' in entry:
            datetime_str = entry.pop('date-time')
            _assert_type(datetime_str, str, 'date-time')
            date_time = self.parse_datetime(datetime_str, tzinfo=tz,
                                            fold=fold)
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
        if date_time.tzinfo is None:
            raise LoadError('time zone is not provided')
        if date_time.tzinfo.utcoffset(date_time) is None:
            raise LoadError(f'{date_time.tzinfo!r} returns None for '
                            f'utcoffset()')

        # Do not link to the panel yet (so that user can override this method
        # and return a None instead if an entry is not desired)
        obj = Entry(date_time)

        # Process 'data' or 'input'
        self._process_entry_data(obj, entry, attrs)

        # Optional fields
        # ---------------
        # Insight
        insight = entry.pop('insight', False)
        _assert_type(insight, bool, 'insight')
        obj.insight = insight

        # Title
        if 'title' in entry:
            title = entry.pop('title')
            _assert_type(title, str, 'title')
            obj.set_title(title)

        # Caption
        if 'caption' in entry:
            caption = entry.pop('caption')
            _assert_type(caption, str, 'caption')
            obj.set_attribute('caption', caption)

        # Question
        if 'question' in entry:
            question = entry.pop('question')
            _assert_type(question, str, 'question')
            obj.set_attribute('question', question)

        # Transcription
        if 'transcription' in entry:
            text = entry.pop('transcription')
            # Since transcriptions usually are long...
            text = _ensure_text(text, 'transcription')
            obj.set_attribute('transcription', text)

        if entry:
            keys_str = ', '.join(sorted(map(str, entry.keys())))
            plural = '' if len(entry) == 1 else 's'
            self._warn(f'ignored entry key{plural}: {keys_str}',
                       LoadWarning)

        return obj

    # To keep the naming consistent I'm using 'obj' for the Entry instance.
    def _process_entry_data(self, obj, entry, attrs):
        # Type and format
        if 'type-format' in entry:
            type_format = entry.pop('type-format')
            _assert_type(type_format, str, 'type-format')
            type_, fmt = type_format.split('-', 1)
        else:
            if 'type' in entry:
                type_ = entry.pop('type')
                _assert_type(type_, str, 'type')
                type_ = datatypes.alias_check(type_)
            else:
                type_ = None

            if 'format' in entry:
                fmt = entry.pop('format')
                _assert_type(fmt, str, 'format')
            else:
                fmt = None

        # Encoding
        if 'encoding' in entry:
            enc = entry.pop('encoding')
            _assert_type(enc, str, 'encoding')
        else:
            # None just means the encoding wasn't provided.
            enc = None

        # Data and input
        if 'data' in entry and 'input' in entry:
            raise LoadError("only one of 'data' and 'input' can be "
                            "specified")
        elif not ('data' in entry or 'input' in entry):
            raise LoadError("at least one of 'data' and 'input' "
                            "should be specified")

        # The algorithm for inference is still very akin to basicproc.py
        # Check out 0.md if you wanna see how that works (i spent quite
        # a lot of effort on it ;-;)
        if 'data' in entry:
            data = entry.pop('data')
            data = _ensure_text(data, 'data')
            if 'data-encoding' in entry:
                data_enc = entry.pop('data-encoding')
                _assert_type(data_enc, str, 'data-encoding')
                try:
                    func = self.get_data_encoder(data_enc)
                except LookupError:
                    raise LoadError(f'invalid data encoding: '
                                    f'{data_enc!r}') from None
                raw = func(data.encode('ascii'))
                if type_ is None:
                    type_ = self._infer_type_from_encoding(enc)
                if enc is None:
                    enc = self._infer_encoding_from_type(type_)
            else:
                if not (enc is None or enc == 'utf-8'):
                    self._warn(f"'data': encoding {enc!r} treated as "
                               f"'utf-8'", LoadWarning)
                enc = 'utf-8'
                raw = data.encode(enc)
                # No need to go through the hassle of calling
                # _infer_type_from_encoding since we know that
                # enc == 'utf-8'...
                if type_ is None:
                    type_ = 'plain'
            obj.set_raw_data(raw)
        else:
            path = entry.pop('input')
            _assert_type(path, str, 'input')
            obj.set_source(self._find_path(path, attrs['paths']))
            if type_ is None:
                type_ = self._infer_type_from_input_path(path)
            if type_ is None:
                type_ = self._infer_type_from_encoding(enc)
            if enc is None:
                enc = self._infer_encoding_from_type(type_)

        obj.set_type(type_)
        obj.set_format(fmt)
        obj.set_encoding(enc)

        # Metadata
        # --------
        # Creation time
        meta = entry.pop('meta', {})
        obj_meta = {}

        # Posted time (specific to the Perspective app)
        # The default value of obj.date_time is already set by types.Entry,
        # so we only need to handle non-default cases here.
        if 'posted' in meta:
            posted = meta.pop('posted')
            _assert_type(posted, str, 'posted')
            obj.set_meta_attribute(
                'posted', self.parse_datetime(
                    posted, tzinfo=obj.date_time.tzinfo,
                    fold=obj.date_time.fold))

        # Creation time
        if 'created' in meta:
            created = meta.pop('created')
            _assert_type(created, str, 'created')
            time_created = self.parse_datetime(
                created, tzinfo=obj.date_time.tzinfo,
                fold=obj.date_time.fold)
        else:
            time_created = None

        obj.set_meta_attribute('created', time_created)

        if 'modified' in meta:
            modified = meta.pop('modified')
            _assert_type(modified, str, 'modified')
            time_modified = self.parse_datetime(
                modified, tzinfo=obj.date_time.tzinfo,
                fold=obj.date_time.fold)
        else:
            time_modified = time_created

        obj.set_meta_attribute('modified', time_modified)

        # Description
        desc = meta.pop('desc', '')
        obj.set_meta_attribute('desc', _ensure_text(desc, 'desc'))

        for key, value in meta.items():
            obj.set_meta_attribute(key, copy.deepcopy(value))

    # This is a protected method (hence the single underscore)!
    def _find_path(self, path, dirpaths):
        base = self.get_option('base_dir')
        candidates = []
        break_loop = False  # *sad goto noises*
        for pattern in dirpaths:
            # Append `os.sep` to ensure glob looks for directories only
            pattern = os.path.abspath(os.path.join(base, pattern)) + os.sep
            for dirpath in glob.iglob(pattern):
                filepath = os.path.normpath(os.path.join(dirpath, path))
                if os.path.isfile(filepath):
                    candidates.append(filepath)
                    if not self.get_option('warn_ambiguous_paths'):
                        break_loop = True
                        break
            if break_loop:
                break

        try:
            first = candidates[0]
        except IndexError:
            raise LoadError(f'cannot find path {path!r}') from None

        # From the for loop above, since having warn_ambiguous_paths = False
        # would break the loop after the first match, it would imply that
        # matches more than 1 means that duplicates are found.
        #
        # Note that this might raise an exception if the 'paths' variable
        # are ill-defined (like ['img', '*']; both of the paths would match
        # the directory 'img').
        if len(candidates) > 1:
            self._warn(f'found more than one path for {path!r}; '
                       f'using the first path found {first!r}', LoadWarning)
        return first

    ### Inference ###
    @staticmethod
    def _infer_type_from_encoding(enc, default='binary'):
        """Infer type from encoding.  Always succeeds unless `enc` is None,
        in which case `default` is returned.
        """
        if enc is None:
            return default
        return 'binary' if enc == 'binary' else 'plain'

    @staticmethod
    def _infer_type_from_input_path(path, default=None):
        try:
            return datatypes.path_to_type(path)
        except LookupError:
            return default

    @staticmethod
    def _infer_encoding_from_type(type_):
        # assert type_ is not None
        try:
            is_text = datatypes.is_text_type(type_)
        except LookupError:
            is_text = False
        return 'utf-8' if is_text else 'binary'

    def get_data_encoder(self, data_enc):
        """Return data encoding given its name as a string.
        Raise LookupError on an invalid data encoding.
        """
        # This raises KeyError which is a subclass of LookupError
        return _data_enc_table[data_enc]

    # Options checker...
    def check_paths_option(self, paths):
        if not isinstance(paths, (list, tuple)):
            raise ValueError(f'paths should be a list or tuple, '
                             f'not {paths!r}')
        return tuple(paths)

    # These are simply convenient checking that I just like to keep here XD
    # These are private simply because I don't see any point in subclassing
    # these... (although a `check_hook` could be called every time a panel
    # is added... but again I don't see the point.  Yet.)
    def __check_panel_order(self, panels):
        if len(panels) < 2:
            # This is just the first panel.  No need to compare!
            return
        # Since this is called every time a new panel is added, we only
        # need to compare the last two panels :D
        panel_1, panel_2 = panels[-2:]
        length = len(panels)
        # Hooman index!  Maybe?
        index_1, index_2 = length - 1, length
        if panel_1.date > panel_2.date:
            self._warn('panel #{} ({}) is after panel #{} ({})'
                       .format(index_1, panel_1.date, index_2, panel_2.date),
                       LoadWarning)
        if panel_1.date == panel_2.date:
            self._warn('panel #{} is equal to panel #{} ({})'
                       .format(index_1, index_2, panel_2.date),
                       LoadWarning)

    def __check_panel_duplicates(self, panels):
        # Make a dict with date as keys and indices as values
        panel_dict = collections.defaultdict(list)
        for index, panel in enumerate(panels, start=1):
            panel_dict[panel.date].append(index)

        for panel_date, indices in sorted(panel_dict.items()):
            if len(indices) > 1:
                if len(indices) == 2:
                    index_str = ' and '.join(map(int, indices))
                else:
                    index_str = ', '.join(map(int, indices))
                self._warn(f'panels {index_str} are share the same date '
                           f'{panel_date}', LoadWarning)

    def __check_entry_order(self, panel):
        # Stolen from basicproc.py
        main_entries = []
        insight_entries = []

        has_switched = False
        expected_insight_value = None
        last_main_entry = None
        last_insight_entry = None
        # We have plenty of space so I changed i to index
        for index, entry in enumerate(panel.entries(), start=1):
            if expected_insight_value is None:
                expected_insight_value = entry.insight

            # Checking main -> insight order
            if expected_insight_value != entry.insight:
                if has_switched:
                    expected = ('an insight entry' if expected_insight_value
                                else 'a main entry')
                    got = ('an insight entry' if entry.insight
                           else 'a main entry')
                    msg = (f'expected entry {index} to be {expected}, '
                           f'got {got} (on {panel.date})')
                    self._warn(msg, LoadWarning)
                else:
                    has_switched = True
                    expected_insight_value = entry.insight

            # Checking main entry order
            if last_main_entry is not None and not entry.insight:
                if last_main_entry.date_time > entry.date_time:
                    msg = (f'inconsistent order in main entries '
                           f'on {panel.date} (entry {index} precedes '
                           f'entry {index - 1} in time)')
                    self._warn(msg, LoadWarning)

            # Checking insight entry order
            if last_insight_entry is not None and entry.insight:
                if last_insight_entry.date_time > entry.date_time:
                    msg = (f'inconsistent order in insight entries '
                           f'on {panel.date} (entry {index} precedes '
                           f'entry {index - 1} in time)')
                    self._warn(msg, LoadWarning)

            if entry.insight:
                last_insight_entry = entry
            else:
                last_main_entry = entry

    # Method hooks
    def parse_datetime(self, s, *, tzinfo, fold):
        return timeutil.parse_datetime(s, tzinfo=tzinfo, fold=fold)

    def parse_time(self, s, *, tzinfo, fold):
        return timeutil.parse_time(s, tzinfo=tzinfo, fold=fold)

    def parse_date(self, s):
        return timeutil.parse_date(s)


class JSONDumper:
    __slots__ = ('_all_options', '_options',)

    def __init__(self, **options):
        self._all_options = {
            'json_options', 'backup_name',
            'default_time_zone_offset', 'paths',
        }
        self._options = {
            'backup_name': 'backup.json',
            'json_options': dict(
                ensure_ascii=False,
                indent=2,
                sort_keys=False,
            ),
            # Time zone
            #
            # When this is None, JSONDumper does not attempt to set a global
            # variable for the entries (every entry has its own time zone).
            #
            # When this is set, it should be a datetime.timedelta() object!
            # (and it should be strictly between -24 hours and 24 hours)
            # A global variable for the time zone is then set globally, and
            # if the offset is different from this one, it is then explicitly
            # written out in each entry.
            #
            'default_time_zone_offset': None,
            'paths': ('assets',),

            # Description (as a fixed string)
            'desc': '',
        }
        self.configure(**options)

    def configure(self, **options):
        invalid = options.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            plural = '' if len(invalid_str) == 1 else 's'
            raise ValueError(f'invalid key{plural}: {invalid_str}')
        for k, v in options.items():
            try:
                checker = getattr(self, f'check_{k}_option')
            except AttributeError:
                pass
            else:
                v = checker(v)
            self._options[k] = v

    def get_option(self, name):
        return self._options[name]

    def check_paths_option(self, paths):
        if isinstance(paths, str):
            raise TypeError(f'paths should be an iterable of str, not str')
        return tuple(paths)

    # INTERFACES FOR DUMPING:
    # 1.  a list of Panel() objects
    #     each entry will call back the method get_entry_filename(), which
    #     can be overridden if needed.  The following dump() method
    #     implements this.
    #
    # 2.  a list of Panel() objects, joined with a list of export paths
    #     this is exposed as the basic_dump() method
    def dump(self, panels, dirname, *, encoding='utf-8'):
        os.mkdir(dirname)
        panels = list(panels)
        files_added = set()
        export_paths = []
        for panel in panels:
            for entry in panel.entries():
                rv = self.get_entry_filename(entry, panel, files_added.copy())
                if rv is None:
                    export_paths.append(None)
                else:
                    root, filename = rv
                    files_added.add(root)
                    export_paths.append(filename)

        try:
            self.__basic_dump(panels, export_paths, dirname, encoding)
        except:
            self.__cleanup(dirname)
            raise

    # Low-level interface (lower than ever!)
    def basic_dump(self, panels, export_paths, dirname,
                   *, encoding='utf-8'):
        os.mkdir(dirname)
        panels = list(panels)
        try:
            self.__basic_dump(panels, export_paths, dirname, encoding)
        except:
            self.__cleanup(dirname)
            raise

    def dumps(self, panels):
        panels = list(panels)
        data = self.__basic_dump_data(panels, (), os.devnull)
        if 'paths' in data:
            del data['paths']
        return json.dumps(data, **self.get_option('json_options'))

    def __basic_dump(self, panels, export_paths, dirname, encoding):
        data = self.__basic_dump_data(panels, export_paths, dirname)
        backup_name = self.get_option('backup_name')
        backup_path = os.path.normpath(os.path.join(dirname, backup_name))
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        with io.open(backup_path, 'x', encoding=encoding) as fp:
            json.dump(data, fp, **self.get_option('json_options'))
            fp.write('\n')

    # XXX: Should we allow user to dump duplicate paths or paths that
    # are the same as backup_name??
    def __basic_dump_data(self, panels, export_paths, dirname):
        input_paths = []
        paths = list(self.get_option('paths'))
        dirname = os.path.abspath(dirname)

        relative_paths = []
        for i, path in enumerate(export_paths, start=1):
            if path is None:
                relative_paths.append(None)
            else:
                name = f'export path {i}'
                apath, rpath = self.__check_path(dirname, path, name)
                relative_paths.append(rpath)

        # TODO: Make this an option
        shorten_paths = True
        if shorten_paths:
            input_paths = self.__compute_input_paths(relative_paths, paths)
        else:
            input_paths = relative_paths

        panels = list(panels)
        data = self.prepare_backup(panels)

        panel_dicts = []
        path_it = zip(export_paths, input_paths)
        for panel in panels:
            panel_dict, panel_entries = self.wrap_panel(panel)
            for entry in panel.entries():
                entry_dict = self.wrap_entry(entry, panel)
                relative_path, input_path = next(path_it, (None, None))
                if relative_path is None:
                    self.write_entry_data(entry_dict, entry)
                else:
                    export_path = os.path.join(dirname, relative_path)
                    self.export_entry(entry_dict, entry,
                                      export_path, input_path)
                if entry_dict is not None:
                    panel_entries.append(entry_dict)
            if panel_dict is not None:
                panel_dicts.append(panel_dict)

        data['data'] = panel_dicts
        return data

    def __compute_input_paths(self, relative_paths, paths):
        # Take the shortcut if every file were unique
        basenames = [os.path.basename(p) for p in relative_paths
                     if p is not None]
        if len(basenames) == len(set(basenames)):
            unique_names = True
        else:
            unique_names = False

        input_paths = []
        for rpath in relative_paths:
            if rpath is None:
                # Just add a placeholder
                input_paths.append(None)
                continue
            parts = []
            path = rpath
            while path:
                path, name = os.path.split(path)
                parts.append(name)
            parts.reverse()

            # This part might be a bit hard to grasp... so let me give some
            # concrete examples.
            #
            # Suppose we have relative_paths = ['a/1.txt', 'b/1.txt'] and
            # paths = ['a', 'b'], then there's an ambiguity if we had made
            # input paths all '1.txt'.  For example, if we specified 'a/1.txt'
            # as '1.txt', then it would match against both paths.
            # The only way we may specify this is by specifying
            # ['a/1.txt', 'b/1.txt'].
            #
            # Now suppose this time we have relative_paths
            # = ['a/1.txt', 'a/b/1.txt'] and paths = ['a'].  In this case we
            # would actually be safe to specify 'a/1.txt' as '1.txt' since it
            # would never be matched against 'a/b/1.txt'.  Then we find
            # 'b/1.txt' to be the only way to specify 'a/b/1.txt' since, when
            # we try to pick the shortest component, '1.txt', it doesn't work
            # because we only have 'a' in the path.
            #
            # What happens below is the precisely the process of finding the
            # "right" path I said here...
            for i in reversed(range(len(parts))):
                # Start by checking all the possible sub-paths that are NOT
                # the path itself.  For example, for 'a/b/c/1.txt' we check
                # '1.txt', 'c/1.txt', then 'b/c/1.txt' and finally
                # 'a/b/c/1.txt'.
                test_path = os.path.join(*parts[i:])
                test_dir = os.path.join(*parts[:i] or ['.'])
                # Boolean to keep track of whether we are able to find this
                # path.  We don't have to worry about finding this path
                # multiple times as long as we can ensure in the check after
                # this that we can ONLY find this path and nothing else.
                reachable = False
                for path_pat in paths:
                    if fnmatch.fnmatch(test_dir, path_pat):
                        reachable = True
                        break
                # If we never find this path, it's probably not reachable;
                # (like the case of relative_path = ['a/b/1.txt'],
                # paths = ['a'], and test_path = '1.txt'); this is the business
                # left for the next iteration/code outside this loop.  If there
                # are more than one matches (like the case of relative_path
                # = ['a/1.txt'] and paths = ['a', '*']), then perhaps the
                # 'paths' are ill-defined, but it is still possible that the
                # match for THIS specific path is unique.
                #
                # Either way, we say a path is okay if we find at least one
                # match this way.  It is the following check that is the most
                # important...
                if reachable:
                    # no_match is True ONLY if 'test_path' is unambiguous;
                    # that is it, combined with all possible prefixes in
                    # 'paths', it never matches any other path in
                    # 'relative_paths'.
                    no_match = True
                    test_path_esc = glob.escape(test_path)
                    if not unique_names:
                        for dir_pattern in paths:
                            pattern = os.path.join(dir_pattern, test_path_esc)
                            for other in relative_paths:
                                if (other != rpath and
                                        fnmatch.fnmatch(other, pattern)):
                                    no_match = False
                                    break
                    if no_match:
                        input_paths.append(test_path)
                        break
            else:
                raise DumpError(
                    f"{rpath!r} cannot be resolved, likely due to being "
                    f"unreachable with the current 'path' option {paths!r}")
        return input_paths

    @staticmethod
    def __cleanup(dirname):
        if os.path.exists(dirname):
            shutil.rmtree(dirname, ignore_errors=True)

    def prepare_backup(self, panels):
        data = collections.OrderedDict()
        default_offset = self.get_option('default_time_zone_offset')
        data['desc'] = self.get_description()
        if default_offset is not None:
            if not isinstance(default_offset, datetime.timedelta):
                raise TypeError(f"'default_time_zone_offset' should be a "
                                f"datetime.timedelta object, not "
                                f"{default_offset!r}")
            # XXX: Lazy time zone range checking
            datetime.timezone(default_offset)
            data['tz'] = timeutil.format_offset(default_offset)
        paths = list(self.get_option('paths'))
        if paths:
            data['paths'] = paths
        return data

    def get_description(self):
        desc = self.get_option('desc')
        if desc:
            optional = f'  Description: {desc}'
        else:
            optional = ''
        timestr = self.get_current_time_string()
        return f'This is a backup file exported at {timestr}.{optional}'

    # Helper... subclass-method-ish thingy?
    def get_current_time_string(self):
        offset = self.get_option('default_time_zone_offset')
        if offset is not None and offset:
            tz = datetime.timezone(offset)
            base = datetime.datetime.now().astimezone(tz).ctime()
            return f'{base} (UTC{timeutil.format_offset(offset)})'
        utc = datetime.timezone.utc
        base = datetime.datetime.now().astimezone(utc).ctime()
        return f'{base} (UTC)'

    # They are split up into two parts so that subclassing life can be easier!
    def get_entry_filename(self, entry, panel, added):
        # Keep text entries by default
        if entry.is_text():
            return
        root, filename = self.basic_get_entry_filename(
            entry, panel, added, 'assets')
        return root, os.path.join('assets', filename)

    def basic_get_entry_filename(
            self, entry, panel, added, dirname, extension=None):
        base_name = (entry.date_time.replace(tzinfo=None)
                     .isoformat(sep='_').replace(':', '-'))
        if entry.date_time.date() != panel.date:
            base_name = panel.date.isoformat() + '_' + base_name
        file_count = 1
        if extension is None:
            extension = datatypes.get_extension(entry.get_type(), default='')
        # No infinte loops!
        # (Worst case scenario, '1 <= file_count <= len(added)' all
        # coincide with the 'added' set, and the one above it coincides with
        # 'self.backup_name'. This SHOULD however terminate at
        # 'len(added) + 2'...)
        while file_count < len(added) + 3:
            root = f'{base_name}_{file_count}'
            if root not in added:
                filename = os.path.join(dirname, root + extension)
                if filename != self.get_option('backup_name'):
                    return root, root + extension
            file_count += 1
        raise RuntimeError('failed to generate a file name')

    def __check_path(self, dirname, path, name):
        # Absolute path, just to make sure we're on the same level
        apath = os.path.abspath(os.path.join(dirname, path))
        # Make sure we're not exporting somewhere outside of 'dst'
        dirname = os.path.abspath(dirname)
        prefix = os.path.commonpath([apath, dirname])
        if prefix != dirname:
            raise ValueError(f'{name} beyond current directory: '
                             f'{path!r}')
        rpath = os.path.relpath(apath, dirname)
        return apath, rpath

    # ====================
    # IMPORTANT FUNCTIONS!
    # ====================
    def wrap_panel(self, panel):
        """(panel, offset) -> (panel_dict, panel_entries)

        `panel_dict` is a dictionary (JSON object) of the exported panel,
        and `panel_entries` is a list that corresponds to
        `panel_dict['entries']`.
        """
        panel_dict = collections.OrderedDict()
        panel_dict['date'] = self.format_date(panel.date)
        rating = panel.get_attribute('rating')
        if rating is not None:
            panel_dict['rating'] = rating
        panel_dict['entries'] = entries = []
        return panel_dict, entries

    def wrap_entry(self, entry, panel):
        """(entry, panel, offset) -> (entry_dict)"""
        entry_dict = collections.OrderedDict()
        self.set_entry_time(entry_dict, entry, panel)

        entry_dict['type'] = entry.get_type()
        entry_dict['encoding'] = entry.get_encoding()

        format_ = entry.get_format()
        if format_ is not None:
            entry_dict['format'] = format_

        # Only write if insight is True (since it's False by default)
        if entry.insight:
            entry_dict['insight'] = entry.insight

        if entry.has_title():
            entry_dict['title'] = entry.get_title()

        # Attributes
        question = entry.get_attribute('question', None)
        if question is not None:
            entry_dict['question'] = question

        caption = entry.get_attribute('caption', None)
        if caption is not None:
            entry_dict['caption'] = caption

        transcription = entry.get_attribute('transcription', None)
        if transcription is not None:
            entry_dict['transcription'] = transcription

        meta = self.wrap_meta_dict(entry)
        if meta:
            # Sort it cuz why not???? :D
            entry_dict['meta'] = collections.OrderedDict(sorted(meta.items()))
        return entry_dict

    def wrap_meta_dict(self, entry):
        meta_dict = {}
        meta = entry.get_meta_dict()
        time = entry.date_time

        time_posted = meta.pop('posted')
        time_created = meta.pop('created', None)
        time_modified = meta.pop('modified', None)

        if time_posted != time:
            meta_dict['posted'] = self.format_datetime(time_posted)
        if time_created is not None:
            meta_dict['created'] = self.format_datetime(time_created)
        if time_modified != time_created:
            meta_dict['modified'] = self.format_datetime(time_modified)

        filename = meta.pop('filename', None)
        if filename is not None:
            meta_dict['filename'] = filename

        desc = meta.pop('desc', '')
        if desc:
            meta_dict['desc'] = desc

        for key, value in meta.items():
            if isinstance(value, (int, float, str)):
                meta_dict[key] = value
            elif value is not None:
                meta_dict[key] = str(value)
        return meta_dict

    def format_date(self, d):
        return d.isoformat()

    # NOTE: time and datetime can both be either naive or aware
    # As for the results, well... it depends.  In this case I simply
    # set the time zone within the 'time' and 'date-time' key, though
    # I figured users can override these so that they set the time zone
    # separately in the 'tz' key or something... idk :/
    def handle_time(self, entry_dict, t):
        timespec = 'auto' if t.second or t.microsecond else 'minutes'
        entry_dict['time'] = t.isoformat(timespec)

    def handle_datetime(self, entry_dict, dt):
        timespec = 'auto' if dt.second or dt.microsecond else 'minutes'
        entry_dict['date-time'] = dt.isoformat(' ', timespec)

    def format_datetime(self, dt):
        timespec = 'auto' if dt.second or dt.microsecond else 'minutes'
        return dt.isoformat(' ', timespec)

    def set_entry_time(self, entry_dict, entry, panel):
        entry_time = entry.date_time
        # XXX: Is this okay???
        offset = self.get_option('default_time_zone_offset')
        # Remove tzinfo if the time zone offset matches
        if offset is not None and entry_time.utcoffset() == offset:
            entry_time = entry_time.replace(tzinfo=None)
        # Hide date if possible
        if entry_time.date() == panel.date:
            self.handle_time(entry_dict, entry_time.timetz())
        else:
            self.handle_datetime(entry_dict, entry_time)

    def write_entry_data(self, entry_dict, entry):
        """Write the raw data in `entry` to `entry_dict`."""
        type_ = entry_dict['type']
        enc = entry_dict['encoding']
        if entry.is_text():
            entry_dict['data'] = entry.get_data()
            if type_ == 'plain':
                del entry_dict['type']
            # Encoding is always 'utf-8' in this case!
            del entry_dict['encoding']
        else:
            raw = entry.get_raw_data()
            raw_encoded = base64.b64encode(raw)
            entry_dict['data-encoding'] = 'base64'
            entry_dict['data'] = raw_encoded.decode('ascii')
            if type_ == 'binary':
                del entry_dict['type']
            if datatypes.is_text_type(type_, default=False):
                inferred_enc = 'utf-8'
            else:
                inferred_enc = 'binary'
            if enc == inferred_enc:
                del entry_dict['encoding']
        if 'meta' in entry_dict:
            entry_dict.move_to_end('meta')

    # 'export_path' is an absolute path!
    # 'input_path' is the path relative to the base directory...
    def export_entry(self, entry_dict, entry, export_path, input_path):
        """Export the raw data in `entry` to `export_path`, and then
        add it to `entry_dict`.
        """
        # Create intermediate directories
        os.makedirs(os.path.dirname(export_path), exist_ok=True)

        # Exporting is dangerous, so we have to make sure we're doing the
        # right thing here.  __basic_dump_data() should have joined the
        # path with dirname's absolute path, so we should get an absolute
        # path (otherwise there's something seriously wrong with this program
        # XD)
        if os.path.abspath(export_path) != os.path.normpath(export_path):
            raise RuntimeError(
                'exporting to a relative path: {!r}'.format(export_path))
        entry.export(export_path)

        entry_dict['input'] = input_path
        type_ = entry_dict['type']
        enc = entry_dict['encoding']

        # First the type is inferred from path, if possible.
        # If that was not possible, the type is inferred from the encoding
        # (where type is then guaranteed to be set).
        # Next the encoding is inferred from the current type, if it is unset.
        #
        # In this reverse-inference process, we assume that either 'type'
        # or 'encoding' is not given and the program is left to infer it
        # on its own.  If the inference matches, then we remove the redundant
        # information.
        inferred_type = datatypes.path_to_type(input_path, default=None)
        if inferred_type is not None and inferred_type == type_:
            del entry_dict['type']
            inferred_enc = (
                'utf-8' if datatypes.is_text_type(type_, default=False)
                else 'binary')
            if inferred_enc == enc:
                del entry_dict['encoding']
        else:
            if enc == 'binary':
                inferred_type = 'binary'
            else:
                inferred_type = 'utf-8'

            if inferred_type == type_:
                del entry_dict['type']
            else:
                inferred_enc = (
                    'utf-8' if datatypes.is_text_type(type_, default=False)
                    else 'binary')
                if inferred_enc == enc:
                    del entry_dict['encoding']

        if 'meta' in entry_dict:
            entry_dict.move_to_end('meta')


def load_json(file, date=None, *, encoding='utf-8', **options):
    loader = JSONLoader()
    if isinstance(file, (str, os.PathLike)):
        loader.configure(base_dir=os.path.abspath(os.path.dirname(file)))
    loader.configure(**options)
    return loader.load(file, date=date, encoding=encoding)


def dump_json(panels, dirname, *, encoding='utf-8', **options):
    dumper = JSONDumper()
    dumper.configure(**options)
    return dumper.dump(panels, dirname, encoding=encoding)
