"""String formatter classes for panels and entries."""

import abc
import contextlib
import re
import os

from . import Entry, Panel
from . import timeutil

__all__ = [
    'Formatter', 'PanelFormatter', 'EntryFormatter',
    # convenience functions
    'format_panel', 'format_entry', 'print_panel', 'print_entry',
    # $19 format_bytes() card... who wants it?
    'format_bytes',
]


def _extend_lines(buf, lines):
    for line in lines:
        buf.append(line)
        buf.append('\n')


class Formatter(abc.ABC):
    """String formatter using a text wrapper supporting a constant width.

    Although I've not written any formal explanation, I think it is probably
    worth mentioning that text wrapping does not mean that both `width` and
    `wrapper` are set to None.  _center_paragraph() would still center the
    text according to `width` if _is_wrapping_disabled() returns False, but
    it would not attempt to wrap the text to fit within that width since
    wrapping is disabled.  For example, `width = 80` and `wrapper = None`
    would still work if you called `_center_paragraph('something')`, just
    when 'something' exceeds the length of 80, no wrapping will happen and
    the string would just be passed on as is.

    (By the way, you can set `width` and `wrapper` AFTER creating this
    formatter object by using `self.width = <something>` and
    `self.wrapper = <something>` (where `self` is the name of this instance)!
    I hope I'm clear enough on that...)

    The initialization might be a bit confusing, on the other hand, since
    setting `width` to some value actually gives you a wrapper by default
    (the TextWrapper in standard library).  I think this is useful because
    most of the time you wouldn't want to import from two libraries (for
    this formatter and a text wrapper), and if you just want some line
    wrapping, then just calling Formatter(width=80) should suffice.  (Of
    course Formatter would have to be a concrete subclass instead of this
    abstract base class.)

    After you've instantiated the object, though, this convenient shortcut
    to enabling text wrapping is gone.  You will have to explicitly set
    `width` AND `wrapper` in order for text wrapping to happen.  (You'll
    know it when _is_wrapping_disabled() returns False.)  If you set
    `width` to 80, `wrapper` will not magically become a
    textwrap.TextWrapper object!

    Arguments
    ---------
    width : int or None, default 80
        The width of the wrapper.  If this is an int, text wrapping is
        enabled.  If this is None, text wrapping is disabled, and the
        `wrapper` argument is ignored.

    wrapper : object, optional
        A wrapper object --- any object that implements a wrap() method
        that returns a list of lines (strings) when called with a single
        argument (the text) and whose `width` attribute can be set.

        If this is omitted and `width` is an int, wrapper will be set to
        a textwrap.TextWrapper() instance.  Be noted that has no effect if
        `width` is None (as mentioned above).
    """

    __slots__ = ('_wrapper', '_width', '_all_options', '_options')

    def __init__(self, width=80, wrapper=None):
        if width is None:
            self.width = None
            self.wrapper = None
        else:
            self.width = width
            if wrapper is None:
                import textwrap
                self.wrapper = textwrap.TextWrapper()
            else:
                self.wrapper = wrapper

        self._all_options = {
            'indent', 'strlen', 'line_callback',
        }
        self._options = {
            'indent': '',
            'strlen': len,  # can be replaced by say wcwidth.wcswidth
            'line_callback': str.rstrip,    # called on every line
        }

    @abc.abstractmethod
    def format(self, obj):
        raise NotImplementedError

    def configure(self, **options):
        invalid = options.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            raise ValueError(f'invalid keys: {invalid_str!r}')
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

    @property
    def wrapper(self):
        return self._wrapper

    @wrapper.setter
    def wrapper(self, wrapper):
        if wrapper is not None:
            if not (hasattr(wrapper, 'wrap') and callable(wrapper.wrap)):
                raise TypeError('wrapper should have a wrap() method')
            # At least it should handle a width like 80, right??
            try:
                wrapper.width = 80
            except (AttributeError, ValueError):
                raise TypeError("the 'width' attribute of wrapper should be "
                                "mutable") from None
        self._wrapper = wrapper

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, width):
        if width is None:
            self._width = None
            return
        if not isinstance(width, int):
            raise TypeError(f'width should be an int, not {width!r}')
        if width <= 0:
            raise ValueError('width should be greater than 0')
        self._width = width

    def check_indent_option(self, indent):
        if not isinstance(indent, str):
            raise TypeError(f'indent should be a str, not {indent!r}')
        return indent

    # Synonyms of get_option('indent') and configure(indent=...), but...
    # this is a lot more readable (given just how many times indent is
    # modified in this code)
    def get_indent(self):
        return self._options['indent']

    def set_indent(self, indent):
        self._options['indent'] = self.check_indent_option(indent)

    @contextlib.contextmanager
    def indented(self, extra_indent):
        """A context manager that creates extra indent.
        Indent will be restored on exit.
        """
        old_indent = self.get_indent()
        try:
            self.set_indent(old_indent + extra_indent)
            yield
        finally:
            self.set_indent(old_indent)

    # =================
    # Protected methods
    # =================
    def _is_wrapping_disabled(self):
        """Return whether text wrapping will happen."""
        return self.wrapper is None or self.width is None

    # Low-level wrapper of the wrapper.wrap function (does not strip)
    def _wrap(self, text):
        if self._is_wrapping_disabled():
            return [text] if text else []
        return self.wrapper.wrap(text)

    # The big guy (does strip)
    # (By strip we now mean calling line_callback(); it used to be just
    # simply calling str.rstrip())
    def _wrap_paragraph(self, text, *, prefix='', fillchar=' ',
                        return_empty=False):
        # return_empty = False will ensure that _wrap_paragraph() returns ['']
        # when provided an empty string (as opposed to _wrap())
        strlen = self._options['strlen']
        callback = self._options['line_callback']
        if strlen(fillchar) != 1:
            raise ValueError('fillchar should precisely have length 1')

        if not (prefix or self.get_indent()):
            if return_empty:
                return self._wrap(text)
            return self._wrap(text) or ['']
        indent = self.get_indent()

        prefix_len = strlen(prefix)
        prefix_fill = prefix_len * fillchar
        if not self._is_wrapping_disabled():
            self.wrapper.width = self.width - strlen(indent) - prefix_len
        lines = []
        # Use 'prefix' only on the first iteration
        indent_and_prefix = indent + prefix
        for line in self._wrap(text):
            line = callback(indent_and_prefix + line)
            lines.append(line)
            # Use 'prefix_fill' on every other iteration
            indent_and_prefix = indent + prefix_fill

        if not lines and not return_empty:
            lines.append(callback(indent_and_prefix))
        return lines

    def _center_paragraph(self, text, *, fillchar=' ', return_empty=False):
        strlen = self._options['strlen']
        callback = self._options['line_callback']
        indent = self.get_indent()
        if strlen(fillchar) != 1:
            raise ValueError('fillchar should precisely have length 1')

        # Width can be negative in this case; in general the string itself
        # will be returned if the length of the string is no less than the
        # width.
        width = (self.width or 0) - strlen(indent)
        if not self._is_wrapping_disabled():
            self.wrapper.width = width
        lines = []
        for line in self._wrap(text):
            line = indent + self._center_line(line, width, fillchar)
            lines.append(callback(line))

        if not lines and not return_empty:
            lines.append(callback(indent))
        return lines

    # Something weird about my Python 3.9.6 interpreter is that
    # line.center(width, fillchar) and '{:{}^{}}'.format(line, fillchar,
    # width) do not given the same result... (the former somehow adds more
    # characters to the LEFT instead of to the RIGHT.)  I guess it might
    # be better if I added my own implementation here so that the results
    # produced by the formatter are always the same.
    def _center_line(self, line, width, fillchar=' '):
        strlen = self._options['strlen']
        diff = width - strlen(line)
        if diff > 0:
            left = diff // 2
            right = diff - left
            return ''.join([left * fillchar, line, right * fillchar])
        return line


class PanelFormatter(Formatter):
    def __init__(self, width=80, wrapper=None, **options):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_zone', 'infer_time_zone', 'coerce_time_zone',
            'sort_entries_by', 'reverse_entries', 'entry_indent',
            'time_format', 'date_rating_sep', 'title_entries_vsep',
            'entry_vsep', 'main_insight_entries_vsep',
        })

        def sort_func(entry):
            return entry.date_time

        self.configure(
            base_dir=None,  # none to infer
            # Formats
            sort_entries_by=sort_func,
            reverse_entries=False,
            # Entry format
            entry_indent='',
            time_format='12 hour',

            time_zone=None,
            # convenience made so that it's optional
            # (set this to False to get all time zone
            # explicitly displayed)
            infer_time_zone=True,
            coerce_time_zone=False,

            date_rating_sep='  ',
            title_entries_vsep='\n\n',
            entry_vsep='\n',
            main_insight_entries_vsep='\n\n',
        )
        self.configure(**options)

    def format(self, panel, *, entry_formatter=None, set_options=True):
        if not isinstance(panel, Panel):
            raise TypeError('format() expected a Panel object, got {!r}'
                            .format(panel))

        buf = []
        options = self.get_entry_formatter_options(panel)
        if entry_formatter is None:
            entry_formatter = EntryFormatter(self.width, self.wrapper)
            entry_formatter.configure(**options)
        elif set_options:
            entry_formatter.wrapper = self.wrapper
            entry_formatter.width = self.width
            entry_formatter.configure(**options)

        main_entries = []
        insight_entries = []
        for ent in panel.entries():
            if ent.insight:
                insight_entries.append(ent)
            else:
                main_entries.append(ent)

        key = self.get_option('sort_entries_by')
        if key:
            reverse = self.get_option('reverse_entries')
            main_entries.sort(key=key, reverse=reverse)
            insight_entries.sort(key=key, reverse=reverse)

        # Title
        title = self.get_title(panel)
        lines = self.wrap_title(title)
        _extend_lines(buf, lines)

        if main_entries or insight_entries:
            buf.append(self.get_option('title_entries_vsep'))
        entry_vsep = self.get_option('entry_vsep')

        # Main entries
        if main_entries:
            for entry in main_entries:
                buf.append(entry_formatter.format(entry))
                buf.append('\n')
                buf.append(entry_vsep)
            buf.pop()
            if insight_entries:
                buf.append(self.get_option('main_insight_entries_vsep'))

        # Insight entries
        if insight_entries:
            lines = self.wrap_insight_header(insight_entries)
            _extend_lines(buf, lines)
            for entry in insight_entries:
                buf.append(entry_formatter.format(entry))
                buf.append('\n')
                buf.append(entry_vsep)
            buf.pop()

        buf.pop()

        return ''.join(buf)

    def get_entry_formatter_options(self, panel):
        # infer base dir
        base_dir = self.get_option('base_dir') or os.getcwd()
        time_zone = self.get_option('time_zone')
        self.get_option('infer_time_zone')
        # For convenience, hide all entry time zones if they happen to have
        # the same offset (unless an explicit time zone is provided or
        # infer_time_zone is set to False)
        if (time_zone is None
                and self.get_option('infer_time_zone')
                and panel.has_entries()):
            entries = panel.entries()
            first = next(entries).date_time
            if all(e.date_time.tzinfo == first.tzinfo or
                   e.date_time.utcoffset() == first.utcoffset()
                   for e in entries):
                time_zone = first.tzinfo
        return dict(
            indent=self.get_option('entry_indent'),
            base_dir=base_dir,
            time_format=self.get_option('time_format'),
            label_insight=False,
            time_zone=time_zone,
            coerce_time_zone=self.get_option('coerce_time_zone'),
        )

    # Can be subclassed (public method too!)
    def get_date_string(self, date):
        return date.strftime(f'%A, %B {date.day}, %Y')

    def get_title(self, panel):
        date_str = self.get_date_string(panel.date)
        rating = self.get_rating(panel)
        if rating is None:
            return date_str
        sep = self.get_option('date_rating_sep')
        return f'{date_str}{sep}{rating}'

    def get_rating(self, panel):
        return panel.get_attribute('rating', None)

    def wrap_title(self, title):
        return self._center_paragraph(title)

    def wrap_insight_header(self, insight_entries):
        if len(insight_entries) == 1:
            return ['Insight', '-------']
        return ['Insights', '--------']


class EntryFormatter(Formatter):
    def __init__(self, width=80, wrapper=None, **options):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_zone', 'coerce_time_zone',
            'time_format', 'date_time_sep',
            'entry_title_attr_sep', 'label_insight', 'content_indent',
            'title_content_vsep', 'question_content_vsep',
            'below_content_vsep', 'transcription_indent',
        })

        self.configure(
            base_dir=None,      # None to infer
            time_zone=None,     # None to infer
            coerce_time_zone=False,
            time_format='12 hour',

            date_time_sep='  ',
            entry_title_attr_sep='  ',

            label_insight=False,
            content_indent='  ',
            title_content_vsep='\n',
            question_content_vsep='\n',
            # For both 'caption' and 'transcription'
            below_content_vsep='\n',
            transcription_indent='  ',
        )

        self.configure(**options)

    def check_time_format_option(self, tm_format):
        if tm_format not in {'12 hour', '24 hour'}:
            raise ValueError("time format should be one of '12 hour', "
                             "'24 hour'")
        return tm_format

    def format(self, entry):
        if not isinstance(entry, Entry):
            raise TypeError('format() expected an Entry object, got {!r}'
                            .format(entry))

        buf = []

        # infer base dir
        base_dir = self.get_option('base_dir') or os.getcwd()

        header = self.get_header(entry)
        lines = self.wrap_header(header)
        _extend_lines(buf, lines)

        with self.indented(self.get_option('content_indent')):
            # Title
            title = self.get_entry_title(entry)
            if title is not None:
                _extend_lines(buf, self.wrap_entry_title(entry, title))
                buf.append(self.get_option('title_content_vsep'))

            # Question
            question = self.get_question(entry)
            if question is not None:
                _extend_lines(buf, self.wrap_question(entry, question))
                buf.append(self.get_option('question_content_vsep'))

            # Content
            content_lines = self.wrap_content(entry)
            _extend_lines(buf, content_lines)
            buf.pop()

            # Caption + transcription
            caption = self.get_caption(entry)
            transcription = self.get_transcription(entry)
            if caption is not None or transcription is not None:
                if content_lines:
                    buf.append('\n')
                    buf.append(self.get_option('below_content_vsep'))

            if caption is not None:
                _extend_lines(buf, self.wrap_caption(entry, caption))
                # Remove the last '\n' in case nothing will be formatted
                # after this...
                if transcription is None:
                    buf.pop()

            if transcription is not None:
                text = transcription
                _extend_lines(buf, self.wrap_transcription(entry, text))
                buf.pop()

        return ''.join(buf)

    # The difference between a header and a title here is that a title
    # is merely a time, but the header would be the complete string of
    # information ready to be displayed
    def get_header(self, entry):
        entry_time = entry.date_time
        if entry.has_panel():
            panel_date = entry.panel.date
        else:
            panel_date = entry_time.date()
        title = self.get_title(panel_date, entry_time)

        # Attributes to display after the title
        attrs = self.get_entry_attrs(entry)
        if attrs:
            attr_str = '({})'.format(', '.join(attrs))
            sep = self.get_option('entry_title_attr_sep')
            return title + sep + attr_str
        else:
            return title

    def get_entry_attrs(self, entry):
        attrs = []
        if self.get_option('label_insight') and entry.insight:
            attrs.append('insight')
        if entry.is_text() and entry.get_type() != 'plain':
            attrs.append(entry.get_type())
        return attrs

    # Default implementation (improved from basicproc.py)
    def __get_time_format(self, entry_time):
        time_format = self.get_option('time_format')
        hour = entry_time.hour
        if time_format == '12 hour':
            return f'{(hour-1) % 12 + 1}:%M %p'
        return f'{hour}:%M'

    def __get_time_format_padded(self, entry_time):
        time_format = self.get_option('time_format')
        hour = entry_time.hour
        if time_format == '12 hour':
            return f'{(hour-1) % 12 + 1:2}:%M %p'
        return f'{hour:2}:%M'

    # Short title: just the time
    # Long title: month, day, and time
    # Full title: year, month, day, and time
    def get_short_title(self, entry_time):
        time_format = self.__get_time_format(entry_time)
        return entry_time.strftime(time_format)

    def get_long_title(self, entry_time):
        time_format = self.__get_time_format_padded(entry_time)
        sep = self.get_option('date_time_sep')
        return entry_time.strftime(f'%b %e{sep}{time_format}')

    def get_full_title(self, entry_time):
        time_format = self.__get_time_format_padded(entry_time)
        sep = self.get_option('date_time_sep')
        return entry_time.strftime(f'%b %e, %Y{sep}{time_format}')

    def get_basic_title(self, panel_date, entry_time):
        """get_title() except entry_time is naive"""
        if panel_date.year == entry_time.year:
            if panel_date == entry_time.date():
                return self.get_short_title(entry_time)
            return self.get_long_title(entry_time)
        return self.get_full_title(entry_time)

    def get_title(self, panel_date, entry_time):
        """Return a representing the time of the entry."""
        time_zone = self.get_option('time_zone')
        entry_time_zone = entry_time.tzinfo

        title = None

        display_tz = False
        display_time = entry_time
        # When time zone is not provided, display time zone
        if time_zone is None:
            display_tz = True
        else:
            # Case of coercing time zone
            if self.get_option('coerce_time_zone'):
                display_time = (
                    entry_time.astimezone(time_zone).replace(tzinfo=None))
                title = self.get_basic_title(panel_date, display_time)
            # If we're not coercing and entry's time zone have different
            # offsets, display the time zone.
            # (Comparison of two tzinfo: https://bugs.python.org/issue28601)
            elif not (time_zone == entry_time_zone or
                    time_zone.utcoffset(entry_time) ==
                    entry_time_zone.utcoffset(entry_time)):
                display_tz = True

        if title is None:
            title = self.get_basic_title(
                panel_date, entry_time.replace(tzinfo=None))

        if display_tz:
            title += f' [{self.format_timezone(entry_time)}]'
        # Cheap solution when the fold attribute != 0 >.>
        elif display_time.fold:
            title += f' [fold = {display_time.fold}]'

        return title

    def format_timezone(self, date_time):
        return timeutil.format_offset(date_time.utcoffset())

    def wrap_header(self, header):
        return self._wrap_paragraph(header)

    # TODO: For files like .py and .c (basically SOURCE code) we don't really
    # wanna display them...
    #
    # Or, in general, entries that are too long should be omitted (or at least
    # should have the OPTION to be omitted, like over 3000 words or something)
    #
    # In addition, for files like Markdown indentation should be consistent
    # throughout the entire text... so I was thinking maybe we'd add
    # wrap_* where * is a type of text, and when this class is subclassed
    # you can implement those functions... like that :D
    def wrap_content(self, entry):
        try:
            func = getattr(self, f'wrap_{entry.get_type()}_entry')
        except AttributeError:
            pass
        else:
            return func(entry)

        if entry.is_text():
            return self.wrap_text_content(entry)
        else:
            return self.wrap_binary_content(entry)

    def wrap_text_content(self, entry):
        """Default implementation for wrapping text entries."""
        text = self.get_content(entry)
        lines = []
        for par in text.splitlines():
            wrapped = self._wrap_paragraph(par)
            lines.extend(wrapped)
        return lines

    def get_content(self, entry):
        return entry.get_data()

    def wrap_binary_content(self, entry):
        """Default implementation for wrapping binary entries."""
        file_size = entry.get_raw_data_size()
        size_str = format_bytes(file_size)
        if entry.get_source() is not None:
            path = self.__get_path(entry.get_source())
            text = (f'{entry.get_type()} file sized {size_str} '
                    f'at {path!r}>')
        else:
            text = f'{entry.get_type()} data sized {size_str}>'
        return self._wrap_paragraph(text, prefix='<')

    def __get_path(self, path):
        return os.path.relpath(path, start=self.get_option('base_dir'))

    def get_entry_title(self, entry):
        return entry.get_title()

    def wrap_entry_title(self, entry, title):
        return self._center_paragraph(title)

    def get_question(self, entry):
        return entry.get_attribute('question', None)

    def wrap_question(self, entry, question):
        return self._wrap_paragraph(question, prefix='(Q) ')

    def get_caption(self, entry):
        return entry.get_attribute('caption', None)

    def wrap_caption(self, entry, caption):
        lines = []
        prefix = 'Caption: '
        for par in caption.splitlines():
            wrapped = self._wrap_paragraph(par, prefix=prefix)
            lines.extend(wrapped)
            # len('Caption: ') equals 9
            prefix = ' ' * 9
        return lines

    def get_transcription(self, entry):
        return entry.get_attribute('transcription', None)

    def wrap_transcription(self, entry, transcription):
        lines = self._wrap_paragraph('Transcription:')
        with self.indented(self.get_option('transcription_indent')):
            for par in transcription.splitlines():
                wrapped = self._wrap_paragraph(par)
                lines.extend(wrapped)
        return lines


# =====================
# Convenience interface
# =====================

def format_panel(panel, *, entry_formatter=None, set_options=True,
                 **options):
    formatter = PanelFormatter(**options)
    return formatter.format(panel, entry_formatter=entry_formatter,
                            set_options=set_options)


def format_entry(entry, **options):
    formatter = EntryFormatter(**options)
    return formatter.format(entry)


def print_panel(panel, file=None, **kwargs):
    return print(format_panel(panel, **kwargs), file=file)


def print_entry(entry, file=None, **kwargs):
    return print(format_entry(entry, **kwargs), file=file)


# ==============================
# Code copied from basicproc.py
# ==============================

def default_bytes_formatter(x):
    # x: float -> s: string
    if x < 100.0:
        return format(x, '.3g')
    return format(x, '.1f')


def format_bytes(
        size, unit='tens', sep=' ', formatter=default_bytes_formatter):
    if size == 0:
        return '0 B'
    units = ['B']
    # Multiplier.  (Think of the unit as an embodiment of the multiplier.)
    mult = 1
    if unit == 'tens':
        units.extend(BYTES_TENS_UNITS)
        # Increase by powers of 10**3 and see if it falls in the range
        # [mult, mult * 10**3).
        for suffix in units:
            if mult <= size < mult * 1000:
                break
            mult *= 1000
        # No need to worry about 'suffix' being undefined since 'unit' has
        # at least one item.
        return formatter(size / mult) + sep + suffix
    elif unit == 'twos':
        units.extend(BYTES_TWOS_UNITS)
        # Increase by powers of 2**10 and see if it falls in the range
        # [mult, mult * 2**10).  Bit shifting is used because... computers.
        for suffix in units:
            if mult <= size < mult << 10:
                break
            mult <<= 10
        return formatter(size / mult) + sep + suffix
    else:
        raise ValueError("unit must be either 'tens' or 'twos'")


BYTES_TENS_UNITS = [
    'kB', 'MB', 'GB', 'TB',
    'PB', 'EB', 'ZB', 'YB',
]
BYTES_TWOS_UNITS = [
    'KiB', 'MiB', 'GiB', 'TiB',
    'PiB', 'EiB', 'ZiB', 'YiB',
]

# ====================================
# End of code copied from basicproc.py
# ====================================
