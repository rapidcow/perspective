"""String formatters classes for the data types."""

import re
import os

from . import Entry, Panel
from . import timeutil

__all__ = [
    'PanelFormatter', 'EntryFormatter',
    # convenience functions
    'stringify_panel', 'stringify_entry',
    # Who uses these?
    'format_bytes',
]

# Determine platform thingies that strftime might not work in
# Single digit version
_SD_H = '%-H'
_SD_I = '%-I'
_SD_d = '%-d'
# Space-padded version
_SP_H = '%k'
_SP_I = '%l'
# Space-padded day '%e' seems to work just fine, so I'm not gonna put it here.

import platform
pf = platform.system()
if pf == 'Windows':
    _SD_H = _SP_H = '%H'
    _SD_I = _SP_I = '%I'
    _SD_d = '%d'
del platform, pf


def _extend_lines(buf, lines):
    for line in lines:
        buf.append(line)
        buf.append('\n')


class Formatter:
    """String formatter using a text wrapper supporting a constant width."""
    wrapper = None
    width = None
    indent = ''
    strip_trailing_whitespace = True  # call rstrip on every line

    def __init__(self, width=80, wrapper=None, strlen=None):
        # width is None -> no line wrapping
        if width is None:
            self.wrapper = None
            self.width = None
        else:
            if not isinstance(width, int):
                raise TypeError(f'width should be an int, not {width!r}')
            if wrapper is None:
                import textwrap
                self.wrapper = textwrap.TextWrapper()
            else:
                self.wrapper = wrapper
            self.width = width

        if strlen is None:
            self.strlen = len
        else:
            self.strlen = strlen

        self._all_options = {'indent'}

    def __strip(self, s):
        if self.strip_trailing_whitespace:
            return s.rstrip()
        return s

    def configure(self, **kwargs):
        invalid = kwargs.keys() - self._all_options
        if invalid:
            invalid_str = ', '.join(sorted(invalid))
            raise ValueError(f'invalid keys: {invalid_str!r}')
        for k, v in kwargs.items():
            setattr(self, k, v)

    # Protected methods
    # Low-level wrapper of the wrapper.wrap function (does not strip)
    def _wrap(self, text):
        if self.wrapper is None:
            return [text]
        return self.wrapper.wrap(text)

    # The big guy (does strip)
    def _wrap_paragraph(self, text, *, prefix='', fillchar=' '):
        if not (prefix or self.indent):
            return self._wrap(text)

        indent = self.indent
        if self.wrapper is None:
            return [self.__strip(indent + line) for line in self._wrap(text)]

        prefix_len = self.strlen(prefix)
        width = self.width - self.strlen(indent) - prefix_len
        fill_len = self.strlen(fillchar)
        fill_num, remainder = divmod(prefix_len, fill_len)
        prefix_fill = fill_num*fillchar + ' '*remainder
        if width <= 0:
            raise ValueError('prefix too long')
        try:
            self.wrapper.width = width
            lines = []
            # Use 'prefix' only on the first iteration
            indent_and_prefix = indent + prefix
            for line in self._wrap(text):
                full_line = self.__strip(indent_and_prefix + line)
                lines.append(full_line)
                # Use 'prefix_fill' on every other iteration
                indent_and_prefix = indent + prefix_fill
        finally:
            self.wrapper.width = self.width - self.strlen(self.indent)

        return lines

    def _center_paragraph(self, text, fillchar=' '):
        if self.wrapper is None:
            # Keep in mind that self.width can be None
            # But also Python treats width shorter than the string itself
            # as formatting with no centering at all :D
            indent = self.indent
            width = max(0, (self.width or 0) - self.strlen(indent))
            line = '{}{:{}^{}}'.format(indent, text, fillchar, width)
            return [self.__strip(line)]
        else:
            lines = []
            indent = self.indent
            width = self.width - self.strlen(indent)
            # _wrap_paragraph will complain if width < 0
            for line in self._wrap_paragraph(text):
                full_line = '{}{:{}^{}}'.format(indent, line, fillchar, width)
                lines.append(self.__strip(full_line))
            return lines


class PanelFormatter(Formatter):
    # INHERITED
    # wrapper = None
    # width = None
    # indent = ''

    def __init__(self, width=80, wrapper=None, **kwargs):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_zone', 'coerce_time_zone',
            'sort_entries_by', 'reverse_entries', 'entry_indent',
            'time_format',
        })
        self.base_dir = None  # none for infer

        # Formats
        def sort_entries_by(entry):
            return timeutil.to_utc(entry.date_time)
        self.sort_entries_by = sort_entries_by
        self.reverse_entries = False

        # Entry format
        self.entry_indent = ''
        self.time_format = '12 hour'
        self.time_zone = None
        self.coerce_time_zone = False

        self.configure(**kwargs)

    def format(self, panel, entry_formatter=None):
        if not isinstance(panel, Panel):
            raise TypeError('format() expected a Panel object, got {!r}'
                            .format(panel))

        buf = []

        # infer base dir
        if self.base_dir is None:
            base_dir = os.getcwd()
        else:
            base_dir = self.base_dir

        # infer the time zone
        if self.time_zone is None:
            try:
                time_zone = panel.entries[0].date_time.tzinfo
            except IndexError:
                time_zone = timeutil.get_local_timezone()
        else:
            time_zone = self.time_zone

        if entry_formatter is None:
            entry_formatter = EntryFormatter(
                indent=self.entry_indent,
                width=self.width,
                wrapper=self.wrapper,
                base_dir=base_dir,
                time_format=self.time_format,
                label_insight=False,

                time_zone=time_zone,
                coerce_time_zone=self.coerce_time_zone,
            )

        main_entries = []
        insight_entries = []
        for ent in panel.entries:
            if ent.insight:
                insight_entries.append(ent)
            else:
                main_entries.append(ent)

        if self.sort_entries_by:
            main_entries.sort(key=self.sort_entries_by,
                              reverse=self.reverse_entries)
            insight_entries.sort(key=self.sort_entries_by,
                                 reverse=self.reverse_entries)

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
        date_str = panel.date.strftime(f'%A, %B {_SD_d}, %Y')
        rating = panel.attrs['rating']
        if rating is None:
            return date_str
        return f'{date_str}  {rating}'


class EntryFormatter(Formatter):
    # INHERITED
    # wrapper = None
    # width = None
    # indent = ''

    def __init__(self, width=80, wrapper=None, **kwargs):
        super().__init__(width, wrapper)
        self._all_options.update({
            'base_dir', 'time_format', 'date_time_sep',
            'entry_title_attr_sep', 'label_insight', 'content_indent',
            'question_content_vsep', 'content_caption_vsep',

            'time_zone', 'coerce_time_zone',
        })

        self.base_dir = None  # None to infer
        self.time_zone = None # None to infer
        self.coerce_time_zone = False

        self.time_format = '12 hour'
        self.date_time_sep = '  '
        self.entry_title_attr_sep = '  '

        self.label_insight = False
        self.content_indent = '  '
        self.question_content_vsep = '\n'
        self.content_caption_vsep = '\n'

        self.configure(**kwargs)

    def format(self, entry):
        if not isinstance(entry, Entry):
            raise TypeError('format() expected an Entry object, got {!r}'
                            .format(entry))

        buf = []

        # infer base dir
        if self.base_dir is None:
            base_dir = os.getcwd()
        else:
            base_dir = self.base_dir

        # infer time zone
        if self.time_zone is None:
            time_zone = entry.date_time.tzinfo
        else:
            time_zone = self.time_zone

        title = self._get_title(entry)

        # Potential need to specify time zone
        entry_time_zone = entry.date_time.tzinfo
        entry_time = entry.date_time
        tz_displayed = False
        if not (time_zone == entry_time_zone or
                time_zone.utcoffset(entry_time) ==
                entry_time_zone.utcoffset(entry_time)):
            if self.coerce_time_zone:
                time_coerced = entry_time.astimezone(time_zone)
                title = self._get_title(entry.replace(date_time=time_coerced))
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
        if self.label_insight and entry.insight:
            attrs.append('insight')
        if entry.is_text() and entry.data['type'] != 'plain':
            attrs.append(entry.data['type'])

        if attrs:
            attr_str = '({})'.format(', '.join(attrs))
            header = title + self.entry_title_attr_sep + attr_str
        else:
            header = title

        lines = self._wrap_paragraph(header)
        _extend_lines(buf, lines)

        old_indent = self.indent
        try:
            self.indent += self.content_indent
            # Question
            if entry.attrs['question'] is not None:
                _extend_lines(buf, self.wrap_question(entry))
                buf.append(self.question_content_vsep)

            # Content
            content_lines = self.wrap_content(entry)
            _extend_lines(buf, content_lines)
            buf.pop()

            # Caption
            if 'caption' in entry.data and entry.data['caption'] is not None:
                if content_lines:
                    buf.append('\n')
                    buf.append(self.content_caption_vsep)
                _extend_lines(buf, self.wrap_caption(entry))
                buf.pop()
        finally:
            self.indent = old_indent

        return ''.join(buf)

    # Default implementation (as in basicproc.py)
    def _get_title(self, entry):
        panel_date = entry.panel.date
        entry_time = entry.date_time

        # formats with a '_pad' suffix have a space before the hour
        # (e.g. ' 5:20 AM').  The ones without it don't (e.g. '5:20 AM').
        if self.time_format == '12 hour':
            time_format = f'{_SD_I}:%M %p'
            time_format_pad = f'{_SP_I}:%M %p'
        elif self.time_format == '24 hour':
            time_format = f'{_SD_H}:%M'
            time_format_pad = f'{_SP_H}:%M'
        else:
            self.__bad_time_format()

        if panel_date.year == entry_time.year:
            if panel_date == entry_time.date():
                fmt = time_format
            else:
                fmt = '%b %e{}{}'.format(self.date_time_sep, time_format_pad)
        else:
            fmt = '%b %e, %Y{}{}'.format(self.date_time_sep, time_format_pad)
        return entry_time.strftime(fmt)

    @staticmethod
    def __bad_time_format():
        raise ValueError("time_format should be one of the following "
                         "values: '12 hour', '24 hour'")

    def wrap_question(self, entry):
        return self._wrap_paragraph(entry.attrs['question'],
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
            func = getattr(self, f'wrap_{entry.data["type"]}_entry')
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
            # Don't treat empty lines as nothing
            wrapped = self._wrap_paragraph(par) or ['']
            lines.extend(wrapped)
        return lines

    def wrap_binary_content(self, entry):
        """Default implementation for wrapping binary entries."""
        file_size = self.__get_entry_size(entry)
        size_str = format_bytes(file_size)
        if 'source' in entry.data:
            path = self.__get_path(entry.data['source'])
            text = (f'{entry.data["type"]} file sized {size_str} '
                    f'at {path!r}>')
        else:
            text = f'{entry.data["type"]} data sized {size_str}>'
        return self._wrap_paragraph(text, prefix='<')

    # Internal implementation...
    __indent_pattern = re.compile('^(\s*)(.*)$', flags=re.UNICODE)

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

    @staticmethod
    def __get_entry_size(entry):
        if 'raw' in entry.data:
            return len(entry.data['raw'])
        elif 'source' in entry.data:
            # This CAN be a directory... but I don't think it's our job
            # here to validate that.
            return os.path.getsize(entry.data['source'])
        else:
            raise ValueError(f"cannot get size of entry (data attribute of "
                             f"{entry!r} doesn't have 'raw' or 'source')")

    def __get_path(self, path):
        return os.path.relpath(path, start=self.base_dir)

    def wrap_caption(self, entry):
        caption = entry.data['caption']
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

def stringify_panel(panel, **kwargs):
    formatter = PanelFormatter(**kwargs)
    return formatter.format(panel)


def stringify_entry(entry, **kwargs):
    formatter = EntryFormatter(**kwargs)
    return formatter.format(entry)


# ==============================
# Code copied from basicproc.py
# ==============================

def default_bytes_formatter(x):
    # x: float -> s: string
    if x < 100:
        return format(x, '.3g')
    return format(x, '.1f')


def format_bytes(size, unit='tens', sep=' ',
                 formatter=default_bytes_formatter):
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
        raise ValueError("'unit' must be either 'tens' or 'twos'")


# Only up to terrabyte (TB) is actually used.  Anything above that
# would be unrealistic.
BYTES_TENS_UNITS = [
    'kB', 'MB', 'GB', 'TB',
    # 'PB', 'EB', 'ZB', 'YB',
]
BYTES_TWOS_UNITS = [
    'KiB', 'MiB', 'GiB', 'TiB',
    # 'PiB', 'EiB', 'ZiB', 'YiB',
]

# ====================================
# End of code copied from basicproc.py
# ====================================
