"""String formatter classes for the data types."""

import abc
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
            'strlen': len,  # for people who need CJK characters (like me!)
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
            raise TypeError(f'indent must be a str, not {indent!r}')
        return indent

    def get_indent(self):
        return self._options['indent']

    def set_indent(self, indent):
        self._options['indent'] = self.check_indent_option(indent)

    # =================
    # Protected methods
    # =================
    def _is_wrapping_disabled(self):
        """Return whether text wrapping will happen."""
        return self.wrapper is None or self.width is None

    # Low-level wrapper of the wrapper.wrap function (does not strip)
    def _wrap(self, text):
        if self._is_wrapping_disabled():
            return [text]
        return self.wrapper.wrap(text)

    # The big guy (does strip)
    # (By strip we now mean calling line_callback(); it used to be just
    # simply calling str.rstrip())
    def _wrap_paragraph(self, text, *, prefix='', fillchar=' '):
        strlen = self.get_option('strlen')
        callback = self.get_option('line_callback')
        if not (prefix or self.get_indent()):
            return self._wrap(text)

        indent = self.get_indent()
        if self._is_wrapping_disabled():
            return [callback(indent + line) for line in self._wrap(text)]

        prefix_len = strlen(prefix)
        width = self.width - strlen(indent) - prefix_len
        fill_len = strlen(fillchar)
        fill_num, remainder = divmod(prefix_len, fill_len)
        prefix_fill = fill_num*fillchar + ' '*remainder
        if width <= 0:
            raise ValueError('prefix too long')
        self.wrapper.width = width
        lines = []
        # Use 'prefix' only on the first iteration
        indent_and_prefix = indent + prefix
        for line in self._wrap(text):
            full_line = callback(indent_and_prefix + line)
            lines.append(full_line)
            # Use 'prefix_fill' on every other iteration
            indent_and_prefix = indent + prefix_fill

        return lines

    def _center_paragraph(self, text, fillchar=' '):
        strlen = self.get_option('strlen')
        callback = self.get_option('line_callback')
        if self._is_wrapping_disabled():
            # Keep in mind that self.width can be None
            # But also Python treats width shorter than the string itself
            # as formatting with no centering at all :D
            indent = self.get_indent()
            width = max(0, (self.width or 0) - strlen(indent))
            line = '{}{:{}^{}}'.format(indent, text, fillchar, width)
            return [callback(line)]
        else:
            lines = []
            indent = self.get_indent()
            width = self.width - strlen(indent)
            # _wrap_paragraph will complain if width < 0
            for line in self._wrap_paragraph(text):
                full_line = '{}{:{}^{}}'.format(indent, line, fillchar, width)
                lines.append(callback(full_line))
            return lines


class PanelFormatter(Formatter):
    def __init__(self, width=80, wrapper=None, **options):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_zone', 'coerce_time_zone',
            'sort_entries_by', 'reverse_entries', 'entry_indent',
            'time_format',
        })

        def func(entry):
            return timeutil.to_utc(entry.date_time)

        self.configure(
            base_dir=None,  # none to infer
            # Formats
            # XXX: Does this work???
            sort_entries_by=func,
            reverse_entries=False,
            # Entry format
            entry_indent='',
            time_format='12 hour',
            time_zone=None,
            coerce_time_zone=False,
        )
        self.configure(**options)

    def format(self, panel, entry_formatter=None):
        if not isinstance(panel, Panel):
            raise TypeError('format() expected a Panel object, got {!r}'
                            .format(panel))

        buf = []

        # infer base dir
        base_dir = self.get_option('base_dir') or os.getcwd()

        # infer the time zone
        time_zone = self.get_option('time_zone')
        if not time_zone:
            try:
                time_zone = next(panel.entries()).date_time.tzinfo
            except StopIteration:
                time_zone = timeutil.get_local_timezone()

        if entry_formatter is None:
            entry_formatter = EntryFormatter(
                self.width, self.wrapper,
                indent=self.get_option('entry_indent'),
                base_dir=base_dir,
                time_format=self.get_option('time_format'),
                label_insight=False,
                time_zone=self.get_option('time_zone'),
                coerce_time_zone=self.get_option('coerce_time_zone'),
            )

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
        title_str = self.get_title(panel)
        for par in title_str.splitlines():
            lines = self._center_paragraph(par)
            _extend_lines(buf, lines)

        if main_entries or insight_entries:
            buf.extend('\n\n')

        # Main entries
        if main_entries:
            for entry in main_entries:
                buf.append(entry_formatter.format(entry))
                buf.extend('\n\n')
            if insight_entries:
                # Yes, more space!  (Two empty lines)
                buf.append('\n')
            else:
                # Pop the second '\n' if there's nothing after this
                # (The first will be popped at the end of this function)
                buf.pop()

        # Insight entries
        if insight_entries:
            entry_title = ('Insight' if len(insight_entries) == 1
                           else 'Insights')
            buf.append(entry_title + '\n')
            buf.append('-' * len(entry_title) + '\n')
            for entry in insight_entries:
                buf.append(entry_formatter.format(entry))
                buf.extend('\n\n')
            buf.pop()

        buf.pop()

        return ''.join(buf)

    # Can be subclassed (public method too!)
    def get_title(self, panel):
        date_str = panel.date.strftime(f'%A, %B {panel.date.day}, %Y')
        rating = panel.get_attribute('rating')
        if rating is None:
            return date_str
        return f'{date_str}  {rating}'


class EntryFormatter(Formatter):
    def __init__(self, width=80, wrapper=None, **options):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_format', 'date_time_sep',
            'entry_title_attr_sep', 'label_insight', 'content_indent',
            'question_content_vsep', 'content_caption_vsep',
            'time_zone', 'coerce_time_zone',
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
            question_content_vsep='\n',
            content_caption_vsep='\n',
        )

        self.configure(**options)

    def format(self, entry):
        if not isinstance(entry, Entry):
            raise TypeError('format() expected an Entry object, got {!r}'
                            .format(entry))

        buf = []

        # infer base dir
        base_dir = self.get_option('base_dir') or os.getcwd()
        # infer time zone
        time_zone = self.get_option('time_zone') or entry.date_time.tzinfo

        panel_date = entry.panel.date
        entry_time = entry.date_time
        title = self._get_title(panel_date, entry_time)

        # Potential need to specify time zone
        entry_time_zone = entry.date_time.tzinfo
        tz_displayed = False
        # XXX: Do we use == or is for comparing two tzinfo's?
        # (I found this: https://bugs.python.org/issue28601)
        if not (time_zone == entry_time_zone or
                time_zone.utcoffset(entry_time) ==
                entry_time_zone.utcoffset(entry_time)):
            if self.get_option('coerce_time_zone'):
                time_coerced = entry_time.astimezone(time_zone)
                title = self._get_title(panel_date, time_coerced)
            else:
                offset_str = timeutil.format_offset(entry_time.utcoffset())
                assert offset_str  # should be aware???
                # TODO: Add a offset sep like attribute
                title += f' [{offset_str}]'
                tz_displayed = True

        # Very cheap solution >.>
        if not tz_displayed and entry_time.fold:
            title += ' [fold = {entry_time.fold}]'

        # Attributes to display after the title
        attrs = []
        if self.get_option('label_insight') and entry.insight:
            attrs.append('insight')
        if entry.is_text() and entry.get_type() != 'plain':
            attrs.append(entry.get_type())

        if attrs:
            attr_str = '({})'.format(', '.join(attrs))
            sep = self.get_option('entry_title_attr_sep')
            header = title + sep + attr_str
        else:
            header = title

        lines = self._wrap_paragraph(header)
        _extend_lines(buf, lines)

        old_indent = self.get_indent()
        try:
            self.set_indent(old_indent + self.get_option('content_indent'))
            # Question
            if entry.get_attribute('question', None) is not None:
                _extend_lines(buf, self.wrap_question(entry))
                buf.append(self.get_option('question_content_vsep'))

            # Content
            content_lines = self.wrap_content(entry)
            _extend_lines(buf, content_lines)
            buf.pop()

            # Caption
            if entry.get_attribute('caption', None) is not None:
                if content_lines:
                    buf.append('\n')
                    buf.append(self.content_caption_vsep)
                _extend_lines(buf, self.wrap_caption(entry))
                buf.pop()
        finally:
            self.set_indent(old_indent)

        return ''.join(buf)

    # Default implementation (as in basicproc.py)
    def _get_title(self, panel_date, entry_time):
        # formats with a '_pad' suffix have a space before the hour with
        # only a single digit (e.g. ' 5:20 AM').  The ones without it don't
        # (e.g. '5:20 AM').
        time_format_opt = self.get_option('time_format')
        if time_format_opt == '12 hour':
            # Convert to 12 hour
            hour_12 = (entry_time.hour-1) % 12 + 1
            time_format = f'{hour_12}:%M %p'
            time_format_pad = f'{hour_12:2}:%M %p'
        elif time_format_opt == '24 hour':
            time_format = f'{entry_time.hour}:%M'
            time_format_pad = f'{entry_time.hour:2}:%M'
        else:
            raise ValueError("time_format should be one of the following "
                             "values: '12 hour', '24 hour'")

        if panel_date.year == entry_time.year:
            if panel_date == entry_time.date():
                fmt = time_format
            else:
                fmt = '%b %e{}{}'.format(self.date_time_sep, time_format_pad)
        else:
            fmt = '%b %e, %Y{}{}'.format(self.date_time_sep, time_format_pad)
        return entry_time.strftime(fmt)

    def wrap_question(self, entry):
        return self._wrap_paragraph(entry.get_attribute('question'),
                                    prefix='(Q) ')

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
        text = entry.get_data()
        lines = []
        for par in text.splitlines():
            # Don't treat empty lines as nothing as they usually
            # separate paragraphs
            wrapped = self._wrap_paragraph(par) or ['']
            lines.extend(wrapped)
        return lines

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

    # Internal implementation...
    __indent_pattern = re.compile(r'^(\s*)(.*)$', flags=re.UNICODE)

    def __wrap_with_indent(self, entry):
        text = entry.get_data()
        lines = []
        for par in text.splitlines():
            match = self.__indent_pattern.match(par)
            # Just in case
            if match:
                indent, rest = match.groups()
            else:
                indent, rest = '', par

            wrapped = None  # sentinel
            if indent:
                try:
                    wrapped = self._wrap_paragraph(rest, prefix=indent) or ['']
                except ValueError:  # prefix might be too long
                    pass

            if wrapped is None:
                wrapped = self._wrap_paragraph(par) or ['']
            lines.extend(wrapped)
        return lines

    def wrap_markdown_entry(self, entry):
        return self.__wrap_with_indent(entry)

    def __get_path(self, path):
        return os.path.relpath(path, start=self.base_dir)

    def wrap_caption(self, entry):
        caption = entry.get_attribute('caption')
        lines = []
        prefix = 'Caption: '
        for par in caption.splitlines():
            wrapped = self._wrap_paragraph(par, prefix=prefix) or ['']
            lines.extend(wrapped)
            # len('Caption: ') equals 9
            prefix = ' ' * 9
        return lines


# =====================
# Convenience interface
# =====================

def format_panel(panel, **options):
    formatter = PanelFormatter(**options)
    return formatter.format(panel)


def format_entry(entry, **options):
    formatter = EntryFormatter(**options)
    return formatter.format(entry)


def print_panel(panel, file=None, **options):
    return print(format_panel(panel, **options), file=file)


def print_entry(entry, file=None, **options):
    return print(format_entry(entry, **options), file=file)


# ==============================
# Code copied from basicproc.py
# ==============================

def default_bytes_formatter(x):
    # x: float -> s: string
    if x < 100:
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
