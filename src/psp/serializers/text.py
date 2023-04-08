"""Plain text processors"""
import logging
import io
import itertools
import json
import os
import shlex

from ..types import Configurable
from .. import timeutil


__all__ = ['TextLoader', 'TextDumper', 'load_text', 'dump_text']


class LoadError(ValueError):
    def __init__(self, lineno, msg):
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return f'line {self.lineno}: {self.msg}'


def _is_eol(token):
    return '\n' in token or '\r' in token


# I don't know why itertools doesn't define a negated counterpart of this
def _takeuntil(predicate, iterable):
    return itertools.takewhile(lambda x: not predicate(x), iterable)


# AUGHH i hate different line terminators (LF CRLF CR all that stuff)
def _count_lines(s):
    return len(s.splitlines()) + 1


# XXX More useful docstring
class TextLoader(Configurable):
    """Text -> JSON loader"""

    def __init__(self, **options):
        super().__init__()
        self.configure(**options)
        self._json_decoder = json.decoder.JSONDecoder()

    def loads(self, text):
        return self.load(io.StringIO(text))

    def load(self, fp):
        if isinstance(fp, io.StringIO):
            buffer = fp
        else:
            buffer = io.StringIO(fp.read())

        # punctuation_chars is a Python 3.6+ thing
        lexer = shlex.shlex(fp, punctuation_chars='\n\r')
        lexer.whitespace = ' \t'

        # top level attributes?
        attrs = {}
        last = 0
        while True:
            token = lexer.get_token()
            if token == lexer.eof:
                break
            if _is_eol(token):
                continue
            elif token.upper() == 'TZ':
                attrs['tz'] = self.get_string(buffer, lexer)
            elif token.upper() == 'PATHS':
                attrs['paths'] = self.get_json(buffer, lexer)
            else:
                # preamble over; start parsing the panels
                break
            last = buffer.tell()

        buffer.seek(last)
        return attrs, self.process_panels(buffer, lexer)

    def process_panels(self, buffer, lexer):
        current_panel = None
        while True:
            token = lexer.get_token()
            if token == lexer.eof:
                return
            # empty line / comment
            if _is_eol(token):
                continue
            if token.upper() in ('PANEL', 'DATE'):
                if current_panel is not None:
                    yield current_panel
                current_panel = self.parse_panel_head(buffer, lexer)
                print(current_panel)
            else:
                self.parse_panel_body(current_panel, buffer, lexer)
        if current_panel is not None:
            yield current_panel

    def parse_panel_head(self, buffer, lexer):
        """(buffer, lexer) -> panel dict"""
        # keep old line number before we consume the whole line
        lineno = lexer.lineno
        tokens = list(self.get_tokens(lexer))
        if not tokens:
            raise LoadError(lineno,
                            'expected date in panel head')
        # split date and rating if necessary
        for i in range(len(tokens), 0, -1):
            try:
                date = self.parse_date(' '.join(tokens[:i]))
            except ValueError:
                continue
            rating = None if i == len(tokens) else ' '.join(tokens[i:])
            break
        else:
            raise LoadError(lineno,
                            f'cannot parse tokens: {tokens!r}')

            # this is assuming you don't use alphanumerical stuff
            # like XD as a "rating"
        panel = {'date': timeutil.format_date(date)}
        if rating is not None:
            panel['rating'] = rating
        return panel

    def parse_panel_body(self, panel, buffer, lexer):
        entries = []
        # if encountered ENTRY / INSIGHT token,
        # call process_entry_head() & push into entries
        #   (in this case assert that "panel is not None")
        # otherwise we should enter process_entry_body()
        if entries:
            panel['entries'] = entries

    def process_entry_head(self, buffer, lexer):
        pass

    def process_entry_body(self, buffer, lexer):
        pass

    # types of fields I think will show up commonly
    # (these aren't supposed to be methods eh)
    def get_tokens(self, lexer):
        return _takeuntil(_is_eol, lexer)

    def process_string(self, buffer, lexer):
        return ' '.join(get_tokens(lexer))

    def process_json(self, buffer, lexer):
        curr = buffer.seek()
        try:
            obj, idx = (self._json_decoder
                        .raw_decode(buffer.getvalue(), curr))
        except Exception as exc:
            raise ValueError(lexer.line,
                             'failed to parse JSON') from exc
        lexer.lineno += _count_lines(buffer.read(idx))
        nxt = lexer.get_token()
        if not _is_eol(nxt):
            raise ValueError(lexer.lineno,
                             'expected EOL after JSON literal')
        return obj

    # date & time; they need parsing because we want to
    # convert more friendly format (like Mar 14 and 7 PM)
    # into ISO format recognized by json.py
    #
    # we will not try to parse time zone as that will be
    # reserved for the purpose of serialization and not for
    # regular use
    def parse_date(self, s):
        return timeutil.parse_date(s)  # XXX

    def parse_time(self, s):
        dt = timeutil.parse_datetime(s)
        if is_naive(dt):
            return dt, None
        return dt, psp.timeutil.format_offset(dt.utcoffset())


class TextDumper(Configurable):
    """Text -> JSON dumper"""

    def __init__(self, **options):
        super().__init__()
        self.configure(**options)

    def dumps(self, panels):
        fp = io.StringIO()
        return self.dump(panels, fp)

    def dump(self, panels, fp):
        for panel in panels:
            # NOTE: this is not a substitute for 'rating' in panel!
            # if 'rating' is present and is None, we'd still want to
            # leave it out
            if panel.get('rating', None) is None:
                print('DATE', panel['date'], file=fp)
            else:
                print('DATE', panel['date'], panel['rating'], file=fp)


def load_text():
    pass


def dump_text():
    pass
