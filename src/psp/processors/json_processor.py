"""Processor for JSON archives."""

import base64
import datetime
import glob
import json
import os


from .. import Panel, Entry      # Types from psp.types
from .. import datatypes
from .. import timeutil

__all__ = [
    'JSONLoader', 'JSONDumper',
    'LoadError', 'DumpError', 'LoadWarning',
    'load_json', 'load_json_with_filter', 'dump_json',
]


class LoadError(Exception):
    """Error that occured while loading a JSON archive."""


class LoadWarning(Warning):
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
            _assert_list_type(obj, str, key, extra)
    header = f'{key!r}{extra}'
    clsname = type(obj).__name__
    raise TypeError(f'{header}: expected a str or a list of str, '
                    f'got {clsname!r}')


class JSONLoader:
    """A JSON archive loader.

    The constructor takes no positional arguments.  The keyword arguments
    are passed to the `configure` method.

    NOTE: Don't rely on tweaking the attributes of this class!
    Use the `configure` method when you need to change something, and in
    case you want to access an option... well don't.  They're not supposed
    to be public anyways.  :/
    """
    def __init__(self, **kwargs):
        # TODO: Write documentation for these options
        self._all_options = {
            'get_attributes', 'load_from_file', 'validate',
            'check_duplicate_panels', 'check_panel_order',
            'check_entry_order', 'error_on_warning',
            'paths', 'base_dir', 'encoding', 'json_kwargs',
            'warn_ambiguous_paths',
        }

        self.get_attributes = False
        self.load_from_file = False
        # Checking (not strictly needed)
        self.validate = True
        self.check_duplicate_panels = True
        self.check_panel_order = True
        self.check_entry_order = True
        self.error_on_warning = False
        self.warn_ambiguous_paths = True
        # Convenience stuff (when load() is called with a file path)
        self.encoding = 'utf-8'

        # directories paths to prepend to input paths when they're not found
        self.paths = []
        # the base directory, used as the ROOT of relative paths
        self.base_dir = os.getcwd()
        # decoders for the data-encoding attribute
        self._data_enc_table = {
            'base16': base64.b16decode,
            'base32': base64.b32decode,
            'base64': base64.b64decode,
            'base64_url': base64.urlsafe_b64decode,
            'ascii85': base64.a85decode,
            'base85': base64.b85decode,
        }
        # keyword arguments to pass to json.loads
        self.json_kwargs = {}
        self.configure(**kwargs)

    def configure(self, **kwargs):
        """Configure options.  This method should be called instead of
        directly accessing the underlying attributes.

        (i will one day write the options in a document, just you wait...)
        """
        invalid = kwargs.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            raise ValueError(f'invalid keys: {invalid_str}')
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _warn(self, msg, w):
        """Raise an exception with w(msg) if the `error_on_warning` option
        is set to True, else issue an warning.
        """
        if self.error_on_warning:
            raise w(msg)
        else:
            import warnings
            warnings.warn(msg, w, 2)

    def load(self, file, date=None):
        """Load an archive from a file as a list of `Panel`s.

        If `date` is provided, optimize the loading process by only
        returning the panel on that date.

        Parameters
        ----------
        file : path-like object or file-like object
            May be a file path to the JSON archive to be read (an instance
            of `str` or `os.PathLike`) or a readable file-like object
            (an object with a `read` method that returns the file content
            as a `str`).

        date : datetime.date object or object, optional
            A `datetime.date` instance or a `str` representing a date.
            The string must be valid for `timeutil.parse_date`.

        Return
        ------
        If the option `get_attributes` is True:

        -   Return `(panels, attributes)` if `date` is not provided; and
        -   Return `(panel, attributes)` if `date` is provided.

        Else:

        -   Return `panels` if `date` is not provided; and
        -   Return `panel` is `date` is provided.
        """
        content = self.__handle_readable_file(file)
        data = json.loads(content, **self.json_kwargs)
        return self.load_data(data, date)

    def __handle_readable_file(self, file):
        """Handle a path-like or file-like object and return the file
        content on success.
        """
        if isinstance(file, (str, os.PathLike)):
            with open(file, encoding=self.encoding) as fp:
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
            return self.__load_all_data(panels, attrs)
        else:
            if isinstance(date, str):
                date = timeutil.parse_date(date)
            elif not isinstance(date, datetime.date):
                raise TypeError(f'date should be a str or datetime.date '
                                f'object, not {type(date).__name__}')
            return self.__load_single_panel(panels, attrs, date)

    def __split_data(self, data):
        if not isinstance(data, dict):
            raise TypeError('JSON data should be a dictionary')
        data = data.copy()
        # This list is not safe to pop() (as it is a reference to the
        # original list)
        panels = data.pop('data', [])
        _assert_list_type(panels, dict, 'data')

        # The rest of 'data' are attributes.
        attrs = data

        # Make a copy of 'paths' so as to not mutate the original dict,
        # but at the same time assign it to attrs.  This function is not
        # responsible for extending self.paths (but self.process_entry()
        # is).
        if 'paths' in data:
            paths = attrs['paths']
            _assert_list_type(paths, str, 'paths')
            paths = paths.copy()
        else:
            paths = []
        attrs['paths'] = paths

        # Type checking before we pass it on
        if 'tz' in attrs:
            _assert_type(attrs['tz'], str, 'tz', 'top level')

        # A subset of 'attrs' to pass on to process_panel
        keys_to_pass = {'paths', 'tz'}
        panel_attrs = {k: v for k, v in attrs.items() if k in keys_to_pass}
        return panels, panel_attrs

    def __load_all_data(self, panels, attrs):
        output = []
        start_with = 0      # index to start checking duplicates with
        for panel_dict in panels:
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
            if self.validate:
                try:
                    panel.validate()
                    for ent in panel.entries:
                        ent.validate()
                except (TypeError, ValueError) as exc:
                    raise LoadError(
                        f'validation error while processing {panel.date}'
                    ) from exc
            output.append(panel)

            if self.check_panel_order:
                self.__check_panel_order(output)
            elif self.check_duplicate_panels:
                start_with = self.__check_duplicate_panels(output, start_with)
            if self.check_entry_order:
                self.__check_entry_order(panel)

        if self.get_attributes:
            return attrs, output
        else:
            return output

    def __load_single_panel(self, panels, attrs, date):
        # TODO: Implement check duplicate panels/panel order
        for panel_dict in panels:
            try:
                panel_date = timeutil.parse_date(panel_dict['date'])
            except (KeyError, TypeError, ValueError):
                # XXX: Should errors be passed silently?
                continue
            if panel_date == date:
                break
        else:
            raise LookupError(f'cannot find panel with date {date}')

        panel = self.process_panel(panel_dict, attrs)
        if self.check_entry_order:
            self.__check_entry_order(panel)
        if self.get_attributes:
            return attrs, panel
        else:
            return panel

    def load_with_filter(self, file, func):
        content = self.__handle_readable_file(file)
        data = json.loads(content, **self.json_kwargs)
        return self.load_data_with_filter(data, func)

    def load_data_with_filter(self, data, func):
        panels, attrs = self.__split_data(data)
        if not callable(func):
            raise TypeError('func must be a callable')

        output = []
        for panel_dict in panels:
            if func(panel_dict):
                # TODO: should be some error-handling here
                try:
                    panel = self.process_panel(panel_dict, attrs)
                except:
                    raise
                output.append(panel)

        if self.get_attributes:
            return attrs, output
        else:
            return output

    def process_panel(self, panel, attrs):
        """Process a panel.

        Parameters
        ----------
        panel : dict
        attrs : dict
        """
        # Required field
        # --------------
        # Date
        try:
            date_str = panel.pop('date')
        except KeyError:
            raise LoadError('panel must provide date')
        _assert_type(date_str, str, 'date')
        date = timeutil.parse_date(date_str)
        obj = Panel(date)

        # Optional fields
        # ---------------
        # Paths
        if 'paths' in panel:
            paths = panel.pop('paths')
            _assert_list_type(paths, str, 'panels')
        # Time zone
        if 'tz' in panel:
            tz = panel.pop('tz')
            _assert_type(tz, str, 'tz', 'in panel')
            attrs['tz'] = tz
        # Rating
        rating = panel.pop('rating', None)
        _assert_type_or_none(rating, str, 'rating')
        obj.attrs['rating'] = rating

        # Entries
        # -------
        ents = panel.pop('entries', [])

        keys_remaining = panel.keys()
        if keys_remaining:
            keys_str = ', '.join(sorted(keys_remaining))
            raise LoadError(f'unrecognized panel keys: {keys_str}')

        entries = []
        for index, ent in enumerate(ents):
            # 'attrs' is only accessed and not mutated, so no need to copy.
            try:
                entries.append(self.process_entry(obj, ent, attrs))
            except (TypeError, ValueError, LoadError, LoadWarning) as exc:
                raise LoadError(
                    f'error while loading entry #{index}') from exc

        obj.entries = entries
        return obj

    def process_entry(self, panel, entry, attrs):
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
            # None for don't change the fold of the parsed datetime
            fold = None

        if 'date-time' in entry:
            datetime_str = entry.pop('date-time')
            _assert_type(datetime_str, str, 'date-time')
            date_time = timeutil.parse_datetime(datetime_str, tzinfo=tz,
                                                fold=fold)
        elif 'time' in entry:
            time_str = entry.pop('time')
            _assert_type(time_str, str, 'time')
            if 'date' in entry:
                date_str = entry.pop('date')
                _assert_type(date_str, str, 'date')
                date = timeutil.parse_date(date_str)
            else:
                date = panel.date
            time = timeutil.parse_time(time_str, tzinfo=tz, fold=fold)
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

        obj = Entry(panel, date_time)

        # Process 'data' or 'input'
        self._process_entry_data(obj, entry, attrs)

        # Optional fields
        # ---------------
        # Insight
        insight = entry.pop('insight', False)
        _assert_type(insight, bool, 'insight')
        obj.insight = insight

        # Caption
        if 'caption' in entry:
            caption = entry.pop('caption')
            obj.data['caption'] = _ensure_text(caption, 'caption')

        # Question
        if 'question' in entry:
            question = entry.pop('question')
            obj.attrs['question'] = _ensure_text(question, 'question')

        keys_remaining = entry.keys()
        if keys_remaining:
            keys_str = ', '.join(sorted(keys_remaining))
            raise LoadError(f'unrecognized entry keys: {keys_str}')

        return obj

    # To keep the naming consistent I'm using 'obj' for the Entry instance.
    def _process_entry_data(self, obj, entry, attrs):
        # Type and format
        if 'type-format' in entry:
            type_format = entry.pop('type-format')
            _assert_type(type_format, str, 'type-format')
            type_, fmt = type_format.split('-')
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
                    func = self._data_enc_table[data_enc]
                except KeyError:
                    raise ValueError(f'invalid data encoding: '
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
            obj.data['raw'] = raw
        else:
            path = entry.pop('input')
            _assert_type(path, str, 'input')
            # Extend the lookup paths given in attrs['paths'] just
            # before lookup.
            #
            # (XXX: This is quite inefficient since we have to build
            # a new list for every entry... but it doesn't make sense to
            # have a path specific to a list stored somewhere in this
            # class either... so I'm kinda lost.)
            lookup_paths = attrs['paths'] + self.paths
            obj.data['source'] = self._find_path(path, lookup_paths)
            if type_ is None:
                type_ = self._infer_type_from_input_path(path)
            if type_ is None:
                type_ = self._infer_type_from_encoding(enc)
            if enc is None:
                enc = self._infer_encoding_from_type(type_)

        obj.data['type'] = type_
        obj.data['format'] = fmt
        obj.data['encoding'] = enc

        # Metadata
        # --------
        # Creation time
        meta = entry.pop('meta', {})
        obj.meta = {}

        # Creation time: either omitted or a string.
        if 'created' in meta:
            created = meta.pop('created')
            _assert_type(created, str, 'created')
            obj.meta['created'] = timeutil.parse_datetime(
                created, tzinfo=obj.date_time.tzinfo)
        else:
            obj.meta['created'] = None

        # Posting time
        if 'posted' in meta:
            posted = meta.pop('posted')
            _assert_type(posted, str, 'posted')
            obj.meta['posted'] = timeutil.parse_datetime(
                posted, tzinfo=obj.date_time.tzinfo
            )
        else:
            obj.meta['posted'] = obj.date_time

        # Description
        desc = meta.pop('desc', '')
        obj.meta['desc'] = _ensure_text(desc, 'desc')

        # NSFW
        nsfw = meta.pop('nsfw', False)
        _assert_type(nsfw, bool, 'nsfw')
        obj.meta['nsfw'] = nsfw

        # Filename
        if 'filename' in meta:
            filename = meta.pop('filename')
            _assert_type(filename, str, 'filename')
        else:
            filename = None
        obj.meta['filename'] = filename

        keys_remaining = meta.keys()
        if keys_remaining:
            keys_str = ', '.join(sorted(keys_remaining))
            self._warn(f'metadata keys ignored: {keys_str}',
                       LoadWarning)

    def _find_path(self, path, paths):
        if not paths:
            dirpaths = ['.']
        else:
            dirpaths = paths

        base = self.base_dir
        candidates = []
        break_loop = False  # *sad goto noises*
        for pattern in dirpaths:
            # Append 'os.sep' to ensure glob looks for directories only
            pattern = os.path.abspath(os.path.join(base, pattern)) + os.sep
            for dirpath in glob.iglob(pattern):
                filepath = os.path.normpath(os.path.join(dirpath, path))
                if os.path.isfile(filepath):
                    candidates.append(filepath)
                    if not self.warn_ambiguous_paths:
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
        if len(candidates) > 1:
            self._warn(f'found more than one path for {path!r}; '
                       f'using the first path found {first!r}', LoadWarning)
        return first

    ### Inference ###
    @staticmethod
    def _infer_type_from_encoding(enc, default='binary'):
        """Infer type from encoding.  Always succeeds
        unless enc is None, in which case 'default' is returned.
        """
        if enc is None:
            return default
        if enc != 'binary':
            return 'binary'
        else:
            return 'plain'

    @staticmethod
    def _infer_type_from_input_path(path, default=None):
        try:
            return datatypes.path_to_type(path)
        except LookupError:
            return default

    @staticmethod
    def _infer_encoding_from_type(typ):
        if typ is not None:
            try:
                is_text = datatypes.get_is_text(typ)
            except LookupError:
                is_text = False
            return 'utf-8' if is_text else 'binary'
        assert False  # unreachable

    # These are simply convenient checking that I just like to keep here XD
    # These are private simply because I don't see any point in subclassing
    # these... (although a `check_hook` could be called every time a panel
    # is added... but again I don't see the point.  Yet.)
    def __check_panel_order(self, panels):
        if len(panels) < 2:
            # This is just the first panel.  No comparison!
            return
        # Since this is called every time a new panel is added, we only
        # need to compare the last two panels :D
        panel_1, panel_2 = panels[-2:]
        length = len(panels)
        index_1, index_2 = length - 2, length - 1
        if panel_1.date > panel_2.date:
            self._warn('panel #{} ({}) is after panel #{} ({})'
                       .format(index_1, panel_1.date, index_2, panel_2.date),
                       LoadWarning)
        if panel_1.date == panel_2.date:
            self._warn('panel #{} is equal to panel #{} ({})'
                       .format(index_1, index_2, panel_2.date),
                       LoadWarning)

    def __check_duplicate_panels(self, panels, start_with):
        panels = panels[start_with:]
        if len(panels) < 2:
            return
        *panels_before, this_panel = panels
        for index, panel in enumerate(panels_before, start=start_with):
            if panel.date == this_panel.date:
                self._warn('panel #{} is a duplicate of panel #{} ({})'
                           .format(index, len(panels) - 1, panel.date))
                return index
        return start_with

    def __check_entry_order(self, panel):
        # Stolen from basicproc.py
        main_entries = []
        insight_entries = []

        has_switched = False
        expected_insight_value = None
        last_main_entry = None
        last_insight_entry = None
        # We have plenty of space so I changed i to index
        for index, entry in enumerate(panel.entries):
            if expected_insight_value is None:
                expected_insight_value = entry.insight

            # Checking main -> insight order
            if expected_insight_value != entry.insight:
                if has_switched:
                    expected = self.__format_insight(expected_insight_value)
                    got = self.__format_insight(entry.insight)
                    msg = (f'expected entry {index} to be {expected}, '
                           f'got {got} (on {panel.date})')
                    self._warn(msg, LoadWarning)
                else:
                    has_switched = True
                    expected_insight_value = entry.insight

            # Checking main entry order
            if last_main_entry is not None and not entry.insight:
                if (timeutil.to_utc(last_main_entry.date_time)
                        > timeutil.to_utc(entry.date_time)):
                    msg = (f'inconsistent order in main entries '
                           f'on {panel.date} (entry {index} precedes '
                           f'entry {index - 1})')
                    self._warn(msg, LoadWarning)

            # Checking insight entry order
            if last_insight_entry is not None and entry.insight:
                if (timeutil.to_utc(last_insight_entry.date_time)
                        > timeutil.to_utc(entry.date_time)):
                    msg = (f'inconsistent order in insight entries '
                           f'on {panel.date} (entry {index} precedes '
                           f'entry {index - 1})')
                    self._warn(msg, LoadWarning)

            if entry.insight:
                last_insight_entry = entry
            else:
                last_main_entry = entry

    @staticmethod
    def __format_insight(insight):
        return 'an insight entry' if insight else 'a main entry'


class JSONDumper:
    def __init__(self, **kwargs):
        self._all_options = {'json_kwargs'}
        self.json_kwargs = {
            'indent': 2,
        }
        self.configure(**kwargs)

    def configure(self, **kwargs):
        invalid = kwargs.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            raise ValueError(f'invalid keys: {invalid_str}')
        for k, v in kwargs.items():
            setattr(self, k, v)

    def dumps(self, data):
        # NOT COMPLETE AT ALL this is just an example
        output = {'tz': '+08:00'}
        return json.dumps(output, fp, indent=self.indent, **json_kwargs)

    # The signature matches that of json.dump
    def dump(self, data, file):
        content = self.dump(data)
        if isinstance(file, (str, os.PathLike)):
            with open(file, 'w+', encoding='utf-8') as fp:
                fp.write(content)
        elif hasattr(file, 'write'):
            file.write(content)
        else:
            raise TypeError(f'file should be a path-like object or '
                            f'a writable file-like object, not {file!r}')


def load_json(file, date=None, **kwargs):
    loader = JSONLoader()
    if isinstance(file, (str, os.PathLike)):
        kwargs.setdefault('base_dir', os.path.abspath(os.path.dirname(file)))
    loader.configure(**kwargs)
    return loader.load(file, date=date)


def load_json_with_filter(file, func, **kwargs):
    loader = JSONLoader()
    loader.configure(**kwargs)
    return loader.load_with_filter(file, func)


def dump_json(data, file, **kwargs):
    dumper = JSONDumper()
    dumper.configure(**kwargs)
    return dumper.dump(data, file)
