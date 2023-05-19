"""Entries with captions, titles, and transcriptions."""

__all__ = [
    'CaptionEntry', 'CaptionJSONLoader', 'CaptionJSONDumper',
    'CaptionEntryFormatter',
]

import itertools
from psp.serializers.json import JSONLoader, JSONDumper
from psp.serializers.text import TextLoader, TextDumper
from psp.serializers.json import _assert_type, _ensure_text
from psp.stringify import EntryFormatter
from psp.types import Entry


class CaptionEntry(Entry, extname='caption'):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_title(self):
        return self.get_attribute('title')

    def set_title(self, title):
        self.set_attribute('title', title)

    def has_title(self):
        return self.has_attribute('title')

    def delete_title(self):
        return self.delete_attribute('title')

    def get_caption(self):
        return self.get_attribute('caption')

    def set_caption(self, caption):
        self.set_attribute('caption', caption)

    def has_caption(self):
        return self.has_attribute('caption')

    def delete_caption(self):
        return self.delete_attribute('caption')

    def get_transcription(self):
        return self.get_attribute('transcription')

    def set_transcription(self, text):
        self.set_attribute('transcription', text)

    def has_transcription(self):
        return self.has_attribute('transcription')

    def delete_transcription(self):
        return self.delete_attribute('transcription')


_CAPTION_ATTRS = ('title', 'caption', 'transcription')

class CaptionJSONLoader(JSONLoader):
    __slots__ = ()

    def get_entry_extensions(self, entry, panel, attrs):
        extensions = super().get_entry_extensions(entry, panel, attrs)
        if any(attr in entry for attr in _CAPTION_ATTRS):
            extensions.append(CaptionEntry)
        return extensions

    def make_entry(self, entry_class, entry, panel, attrs):
        title = None
        caption = None
        text = None

        if issubclass(entry_class, CaptionEntry):
            # Title
            if 'title' in entry:
                title = entry.pop('title')
                _assert_type(title, str, 'title')

            # Caption
            if 'caption' in entry:
                caption = entry.pop('caption')
                _assert_type(caption, str, 'caption')

            # Transcription
            if 'transcription' in entry:
                text = entry.pop('transcription')
                # Since transcriptions usually are long...
                text = _ensure_text(text, 'transcription')

        obj = super().make_entry(entry_class, entry, panel, attrs)

        if caption is not None:
            obj.set_caption(caption)
        if text is not None:
            obj.set_transcription(text)
        if title is not None:
            obj.set_title(title)
        return obj


class CaptionJSONDumper(JSONDumper):
    __slots__ = ()

    def wrap_entry(self, entry, panel):
        entry_dict = super().wrap_entry(entry, panel)

        try:
            title = entry.get_title()
        except (AttributeError, KeyError):
            pass
        else:
            entry_dict['title'] = title

        try:
            caption = entry.get_caption()
        except (AttributeError, KeyError):
            pass
        else:
            entry_dict['caption'] = caption

        try:
            text = entry.get_transcription()
        except (AttributeError, KeyError):
            pass
        else:
            entry_dict['transcription'] = text

        return entry_dict


class CaptionEntryFormatter(EntryFormatter):
    __slots__ = ()

    def wrap(self, entry):
        buf = []
        header = self.get_header(entry)
        buf.extend(self.wrap_header(header))

        indent = self.get_option('content_indent')
        with self.indented(indent):
            empty_lines = self.wrap_paragraph('') 
            # Title
            title = self.get_entry_title(entry)
            if title is not None:
                buf.extend(self.wrap_entry_title(title))
                vsep = self.get_option('title_content_vsep')
                buf.extend(itertools.chain.from_iterable(
                    itertools.repeat(empty_lines, vsep)))

        content_lines = self.wrap_content(entry)
        buf.extend(content_lines)

        with self.indented(indent):
            # Caption + transcription
            caption = self.get_caption(entry)
            text = self.get_transcription(entry)
            if (caption or text) and content_lines:
                vsep = self.get_option('below_content_vsep')
                buf.extend(itertools.chain.from_iterable(
                    itertools.repeat(empty_lines, vsep)))

            if caption:
                buf.extend(self.wrap_caption(caption))

            if text:
                buf.extend(self.wrap_transcription(text))

        return buf

    # Since get_title() is already defined we have to change the name
    # up a bit here...
    def get_entry_title(self, entry):
        try:
            return entry.get_title()
        except (AttributeError, KeyError):
            return None

    def wrap_entry_title(self, title):
        return self.center_paragraph(title)

    def get_caption(self, entry):
        try:
            return entry.get_caption()
        except (AttributeError, KeyError):
            return None

    def wrap_caption(self, caption):
        lines = []
        prefix = 'Caption: '
        for par in caption.splitlines():
            wrapped = self.wrap_paragraph(par, prefix=prefix)
            lines.extend(wrapped)
            # len('Caption: ') equals 9
            prefix = ' ' * 9
        return lines

    def get_transcription(self, entry):
        try:
            return entry.get_transcription()
        except (AttributeError, KeyError):
            return None

    def wrap_transcription(self, transcription):
        lines = self.wrap_paragraph('Transcription:')
        with self.indented(self.get_option('transcription_indent')):
            for par in transcription.splitlines():
                wrapped = self.wrap_paragraph(par)
                lines.extend(wrapped)
        return lines


# TODO: Checkers again
for name, default in dict(
        title_content_vsep=1,
        below_content_vsep=1,
        transcription_indent='  ',
    ).items():
    CaptionEntryFormatter.add_option(name, default)


class CaptionTextLoader(TextLoader):
    def process_entry_body(self, attrs, entry, token, buffer, lexer):
        for candidate in ('title', 'caption', 'transcription'):
            if token.upper() == candidate.upper():
                entry[candidate.lower()] = self.get_string(buffer, lexer)
                return
        return super().process_entry_body(attrs, entry, token,
                                          buffer, lexer)


class CaptionTextDumper(TextDumper):
    pass
