"""Plain text processors"""
from ..types import Configurable
from .. import timeutil

import datetime
import logging
import io
import itertools
import json
import os

# from shlex import shlex
from collections import deque

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

handler.setFormatter(formatter)
logger.addHandler(handler)


__all__ = ['TextLoader', 'TextDumper', 'load_text', 'dump_text']


class LoadError(ValueError):
    def __init__(self, lineno, msg):
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return f'line {self.lineno}: {self.msg}'


# I don't know why itertools doesn't define a negated counterpart of this
def _takeuntil(predicate, iterable):
    return itertools.takewhile(lambda x: not predicate(x), iterable)


# AUGHH i hate different line terminators (LF CRLF CR all that stuff)
def _count_lines(s):
    return len(s.splitlines()) - 1


_DATETIME_FORMATS = [
    '%Y-%m-%d {}', '%Y/%m/%d {}', '%Y.%m.%d {}',
    '%b %d %Y {}', '%a %b %d %Y {}', '%a %b %d {} %Y',
    '%B %d %Y {}', '%a %B %d %Y {}', '%a %B %d {} %Y',
]
_DATETIME_FORMATS_NO_YEAR = [
    '%m-%d {}', '%m/%d {}',
    '%b %d {}', '%a %b %d {}',
    '%B %d {}', '%a %B %d {}',
]
_DATE_FORMATS = [
    ' '.join(fmt.format('').split()) for fmt in _DATETIME_FORMATS
]
_DATE_FORMATS_NO_YEAR = [
    ' '.join(fmt.format('').split()) for fmt in _DATETIME_FORMATS_NO_YEAR
]
# we will leave fractional seconds to fromisoformat()
_TIME_FORMATS = [
    '%H:%M', '%H:%M:%S', '%H:%M:%S%z',
    '%I:%M %p', '%I:%M:%S %p', '%I:%M:%S%z %p',
]

def _parse_datetime(s, year):
    try:
        return timeutil.parse_datetime(s)
    except ValueError:
        pass
    for dt_format in _DATETIME_FORMATS:
        for tm_format in _TIME_FORMATS:
            fmt = dt_format.format(tm_format)
            try:
                return datetime.datetime.strptime(s, fmt)
            except ValueError:
                pass
    if year is None:
        raise ValueError('unknown year')
    for dt_format in _DATETIME_FORMATS_NO_YEAR:
        for tm_format in _TIME_FORMATS:
            fmt = dt_format.format(tm_format)
            try:
                return (datetime.datetime.strptime(s, fmt)
                        .replace(year=year))
            except ValueError:
                pass
    raise ValueError(f'invalid datetime: {s!r}')


def _parse_time(s):
    try:
        return timeutil.parse_time(s)
    except ValueError:
        pass
    for fmt in _TIME_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    raise ValueError(f'invalid time: {s!r}')


def _parse_date(s, year):
    try:
        return timeutil.parse_date(s)
    except ValueError:
        pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    if year is None:
        raise ValueError('unknown year')
    for fmt in _DATE_FORMATS_NO_YEAR:
        try:
            return (datetime.datetime.strptime(s, fmt)
                    .date().replace(year=year))
        except ValueError:
            pass
    raise ValueError(f'invalid date: {s!r}')


def _join_tokens(tokens, wordchars):
    buffer = []
    was_word = False
    for token in tokens:
        is_word = token[:1] in wordchars
        if not is_word and was_word:
            buffer.pop()
        buffer.append(token)
        if is_word:
            buffer.append(' ')
        was_word = is_word
    if was_word:
        buffer.pop()
    return ''.join(buffer)


def _add_attr(obj, key, value, lineno, name):
    if key in obj:
        raise LoadError(lineno, f'got duplicate {name} value for {key!r}')
    obj[key] = value


_DEBUG = 0


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

        lexer = shlex(buffer, punctuation_chars='\n\r', posix=True)
        lexer.whitespace_split = True
        lexer.whitespace = ' \t'
        if _DEBUG == 69:
            lexer.debug = 69

        # top level attributes?
        attrs = {}
        last = 0
        lineno = lexer.lineno
        for token in lexer:
            if self.is_eol(token):
                continue
            if self.parse_preamble(attrs, token, buffer, lexer):
                break
            last = buffer.tell() - len(lexer._pushback_chars)
            lineno = lexer.lineno

        if all(c == '-' for c in token):
            self.get_string(buffer, lexer)
        else:
            logger.info('preamble over on line %d:', lexer.lineno)
            logger.info(attrs)
            buffer.seek(last, os.SEEK_SET)
            lexer._pushback_chars.clear()
            lexer.lineno = lineno
        panels = list(self.process_panels(attrs, buffer, lexer))
        for key, value in self.get_option('attrs').items():
            attrs.setdefault(key, value)
        if panels:
            attrs['data'] = panels
        return attrs

    # calling this differently because it feels less apropos to
    # call this "top-level ATTRIBUTES" when it's all laid out like this
    def parse_preamble(self, attrs, token, buffer, lexer):
        if (self.is_panel(token) or all(c == '-' for c in token)):
            return True
        tup = token.upper()
        lineno = lexer.lineno
        if tup == 'TZ':
            value = self.get_string(buffer, lexer)
            _add_attr(attrs, 'tz', value, lineno, 'top-level')
            logger.info('set time zone to %s', attrs['tz'])
        elif tup == 'PATHS':
            value = self.get_json(buffer, lexer)
            _add_attr(attrs, 'paths', value, lineno, 'top-level')
            logger.info('set paths to %s', attrs['paths'])
        elif tup == 'YEAR':
            value = int(self.get_string(buffer, lexer))
            _add_attr(attrs, 'year', value, lineno, 'top-level')
            logger.info('set year to %d', attrs['year'])
        elif tup == 'ATTR':
            attrs.update(self.get_json(buffer, lexer))
        elif self.is_entry(token):
            if (tup == 'TIME' and
                    self.peek_token(buffer, lexer).upper() == 'ZONE'):
                lexer.get_token()  # dispose the ZONE token
                value = self.get_string(buffer, lexer)
                _add_attr(attrs, 'tz', value, lineno, 'top-level')
                logger.info('set time zone to %s', attrs['tz'])
            else:
                raise LoadError(lexer.lineno, 'no known panel')
        else:
            attrs[token] = self.get_string(buffer, lexer)
        return False

    def process_panels(self, attrs, buffer, lexer):
        panel = None
        date = None
        for token in lexer:
            # empty line / comment
            if self.is_eol(token):
                continue
            if self.is_panel(token):
                if panel is not None:
                    yield panel
                panel, date = self.parse_panel_head(attrs, buffer, lexer)
            else:
                if not (panel and date):
                    raise LoadError(lexer.lineno, 'no known panel')
                logger.debug('process token in panel %r', token)
                lineno = lexer.lineno
                if not self.is_entry(token):
                    self.parse_panel_body(
                        attrs, panel, date, token, buffer, lexer)

                # if encountered ENTRY / INSIGHT token:
                in_panel = True
                while self.is_entry(token) and in_panel:
                    entry = self.parse_entry_head(
                        attrs, date, token, buffer, lexer)
                    logger.debug('created entry:')
                    logger.debug(entry)
                    try:
                        panel['entries'].append(entry)
                    except KeyError:
                        panel['entries'] = [entry]

                    # keep the necessary information to rewind state
                    # (now that this is in the same function we can
                    # probably do this in a better way, but well...)
                    last = buffer.tell() - len(lexer._pushback_chars)
                    lineno = lexer.lineno
                    for token in lexer:
                        if self.is_panel(token):
                            buffer.seek(last, os.SEEK_SET)
                            lexer._pushback_chars.clear()
                            lexer.lineno = lineno
                            in_panel = False
                            break
                        if self.is_entry(token):
                            break
                        if not self.is_eol(token):
                            self.process_entry_body(
                                attrs, entry, token, buffer, lexer)
                        last = buffer.tell() - len(lexer._pushback_chars)
                        lineno = lexer.lineno

        if panel is not None:
            yield panel

    def parse_panel_head(self, attrs, buffer, lexer):
        """(buffer, lexer) -> panel dict"""
        # keep old line number before we consume the whole line
        tokens = self.get_tokens(buffer, lexer)
        if not tokens:
            raise LoadError(lexer.lineno, 'expected date in panel head')
        # split date and rating if necessary
        logger.debug('panel tokens on line %d', lexer.lineno)
        logger.debug(tokens)
        for i in range(len(tokens), 0, -1):
            candidate = _join_tokens(tokens[:i], lexer.wordchars)
            logger.debug('attempting %r', candidate)
            try:
                date = self.parse_date(candidate, attrs.get('year'))
            except ValueError:
                continue
            if i == len(tokens):
                rating = None
            else:
                rating = _join_tokens(tokens[i:], lexer.wordchars)
            break
        else:
            msg = f'cannot parse tokens: {tokens!r}'
            if not (attrs.get('year') or self.get_option('year')):
                msg += ' (did you forget to specify the year somewhere?)'
            raise LoadError(lexer.lineno, msg)
        logger.info('parsed panel of date %s on line %d',
                    date, lexer.lineno)
        panel = {'date': self.format_date(date)}
        if rating is not None:
            panel['rating'] = rating
        return panel, date

    def parse_panel_body(self, attrs, panel, date, token, buffer, lexer):
        tup = token.upper()
        lineno = lexer.lineno
        if tup == 'ATTR':
            attrs = self.get_json(buffer, lexer)
            panel.update(attrs)
        elif tup in ('RATE', 'RATING'):
            value = self.get_string(buffer, lexer)
            _add_attr(panel, 'rating', value, lineno, 'panel')
        else:
            raise LoadError(lineno, 'invalid panel')

        if 'entries' in panel:
            raise LoadError(lexer.lineno,
                            f'ambiguous token {token!r}; already '
                            f'encountered at least one entry')

    def parse_entry_head(self, attrs, date, token, buffer, lexer):
        tup = token.upper()
        logger.debug('process token in entry head %r', token)
        if tup == 'INSIGHT':
            # insight can be optionally followed by 'ENTRY'
            if self.peek_token(buffer, lexer).upper() == 'ENTRY':
                next(lexer)
            is_insight = True
            logger.info('insight keyword found')
        else:
            is_insight = False
            logger.info('no insight keyword found')
        time_str = self.get_string(buffer, lexer)
        logger.info('attempting to parse %r', time_str)
        time = self.parse_time(time_str, date)
        logger.info('parsed %s on line %d', time, lexer.lineno)
        entry = {}
        if time.date() == date:
            entry['time'] = self.format_time(time)
        else:
            entry['date-time'] = self.format_datetime(time)
        if not timeutil.is_naive(time):
            entry['tz'] = timeutil.format_offset(time.utcoffset())
        if is_insight:
            entry['insight'] = True
        return entry

    def process_entry_body(self, attrs, entry, token, buffer, lexer):
        tup = token.upper()
        logger.debug('process token in entry %r', token)
        lineno = lexer.lineno
        for field in ('type', 'format', 'question',
                      'data', 'data-encoding', 'input'):
            if tup == field.upper():
                value = self.get_string(buffer, lexer)
                _add_attr(entry, field, value, lineno, 'entry')
                return
        if all(c == '<' for c in token[:-1]) and token[-1] in '<|':
            entry_type = self.get_string(buffer, lexer)
            logger.info('type of <<< content is %r on line %d',
                        entry_type, lexer.lineno)
            if entry_type:
                entry['type'] = entry_type
            clip = token[-1] == '|'
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('start multiline content with on line %d%s',
                             lexer.lineno, clip * ' (last EOL clipped)')
            sentinel = '>' * (len(token) - clip)
            lines = []
            # we want to preserve new lines
            for line in buffer:
                lexer.lineno += 1
                if line.strip() == sentinel:
                    logger.debug('end multiline string with '
                                 '%r on line %d',
                                 line, lexer.lineno)
                    break
                lines.append(line)
            else:
                raise LoadError(lexer.lineno,
                                'unexpected EOF while scanning '
                                'for entry data')
            if clip and lines:
                lines[-1] = lines[-1].rstrip('\r\n')
            _add_attr(entry, 'data', ''.join(lines),
                      lineno, 'entry')
        elif tup == 'ATTR':
            entry.update(self.get_json(buffer, lexer))
        else:
            raise LoadError(lexer.lineno,
                            f'invalid entry line (token {token!r})')

    # types of fields I think will show up commonly
    # (these aren't supposed to be methods eh)
    # XXX should these be static????
    def is_eol(self, token):
        return '\n' in token or '\r' in token or token == '#'

    def get_tokens(self, buffer, lexer):
        """Consume and return all tokens up until EOL."""
        tokens = list(_takeuntil(self.is_eol, lexer))
        # shlex gobbled extra characters after EOL,
        # so make sure it "regurgitates"
        if buffer.read(1):
            buffer.seek(buffer.tell() - 2)
            lastchar = buffer.read(1)
            try:
                if lastchar == lexer._pushback_chars[-1]:
                    lexer._pushback_chars.pop()
            except IndexError:
                pass
            buffer.seek(buffer.tell() - 1)
        return tokens

    def peek_token(self, buffer, lexer):
        """Return the next token without consuming it."""
        pos = buffer.tell()
        oldchars = deque(lexer._pushback_chars)
        oldlineno = lexer.lineno
        token = lexer.get_token()
        buffer.seek(pos, os.SEEK_SET)
        lexer._pushback_chars = oldchars
        lexer.lineno = oldlineno
        return token

    def is_panel(self, token):
        return token.upper() in ('PANEL', 'DATE')

    def is_entry(self, token):
        return token.upper() in ('ENTRY', 'INSIGHT', 'TIME')

    def get_string(self, buffer, lexer):
        """Parse a string field."""
        token = self.peek_token(buffer, lexer)
        if all(c == '<' for c in token[:-1]) and token[-1] in '<|':
            token = lexer.get_token()
            # line terminator should be pushed inside lookahead chars
            # if that's the case, buffer should also be pointing to
            # the next line, so we can just continue
            # XXX: does this work for \r\n???
            assert self.is_eol(''.join(lexer._pushback_chars))
            clip = token[-1] == '|'
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('start multiline string with '
                             'token %r on line %d%s',
                             token, lexer.lineno,
                             clip * ' (last EOL clipped)')
            sentinel = '>' * (len(token) - clip)
            lines = []
            # again we want to preserve new lines
            for line in buffer:
                lexer.lineno += 1
                if (line.startswith(sentinel)
                        and line.rstrip() == sentinel):
                    logger.debug('end multiline string with '
                                 '%r on line %d',
                                 line, lexer.lineno)
                    break
                lines.append(line)
            else:
                raise LoadError(lexer.lineno,
                                'unexpected EOF while scanning '
                                'for multiline string')
            if clip and lines:
                lines[-1] = lines[-1].rstrip('\r\n')
            return ''.join(lines)
        tokens = self.get_tokens(buffer, lexer)
        return _join_tokens(tokens, lexer.wordchars)

    def get_json(self, buffer, lexer):
        """Parse a JSON field."""
        curr = buffer.tell()
        try:
            obj, idx = (self._json_decoder
                        .raw_decode(buffer.getvalue(), curr))
        except Exception as exc:
            raise LoadError(lexer.lineno,
                            'failed to parse JSON') from exc
        lexer.lineno += _count_lines(buffer.read(idx - curr))
        nxt = next(lexer)
        if not self.is_eol(nxt):
            raise LoadError(lexer.lineno,
                            'expected EOL after JSON literal, '
                            'got %r', nxt)
        return obj

    # date & time; they need parsing because we want to
    # convert more friendly format (like Mar 14 and 7 PM)
    # into ISO format recognized by json.py
    #
    # we will not try to parse time zone as that will be
    # reserved for the purpose of serialization and not for
    # regular use
    def parse_date(self, s, year=None):
        return _parse_date(s, year or self.get_option('year'))  # XXX

    def parse_time(self, s, date):
        try:
            dt = _parse_datetime(s, date.year)
        except ValueError:
            t = _parse_time(s)
            dt = datetime.datetime.combine(date, t)
        return dt

    def format_date(self, date):
        return timeutil.format_date(date)

    def format_time(self, time):
        return timeutil.format_time(time)

    def format_datetime(self, dt):
        return timeutil.format_datetime(dt)


TextLoader.add_option('year', default=None)
TextLoader.add_option('attrs', default={})


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


# Sigh... i have no choice since i accessed the private variables
# (plus we need to make it so that shlex never attempts to add a
# line number when it encounters \n in the 'a' state)
class shlex:
    "A lexical analyzer class for simple shell-like syntaxes."
    def __init__(self, instream=None, infile=None, posix=False,
                 punctuation_chars=False):
        if isinstance(instream, str):
            instream = io.StringIO(instream)
        if instream is not None:
            self.instream = instream
            self.infile = infile
        else:
            import sys
            self.instream = sys.stdin
            self.infile = None
        self.posix = posix
        if posix:
            self.eof = None
        else:
            self.eof = ''
        self.commenters = '#'
        self.wordchars = ('abcdfeghijklmnopqrstuvwxyz'
                          'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
        if self.posix:
            self.wordchars += ('ßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ'
                               'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ')
        self.whitespace = ' \t\r\n'
        self.whitespace_split = False
        self.quotes = '\'"'
        self.escape = '\\'
        self.escapedquotes = '"'
        self.state = ' '
        self.pushback = deque()
        self.lineno = 1
        self.debug = 0
        self.token = ''
        self.filestack = deque()
        self.source = None
        if not punctuation_chars:
            punctuation_chars = ''
        elif punctuation_chars is True:
            punctuation_chars = '();<>|&'
        self._punctuation_chars = punctuation_chars
        if punctuation_chars:
            # _pushback_chars is a push back queue used by lookahead logic
            self._pushback_chars = deque()
            # these chars added because allowed in file names, args, wildcards
            self.wordchars += '~-./*?='
            #remove any punctuation chars from wordchars
            t = self.wordchars.maketrans(dict.fromkeys(punctuation_chars))
            self.wordchars = self.wordchars.translate(t)

    @property
    def punctuation_chars(self):
        return self._punctuation_chars

    def push_token(self, tok):
        "Push a token onto the stack popped by the get_token method"
        if self.debug >= 1:
            print("shlex: pushing token " + repr(tok))
        self.pushback.appendleft(tok)

    def push_source(self, newstream, newfile=None):
        "Push an input source onto the lexer's input source stack."
        if isinstance(newstream, str):
            newstream = io.StringIO(newstream)
        self.filestack.appendleft((self.infile, self.instream, self.lineno))
        self.infile = newfile
        self.instream = newstream
        self.lineno = 1
        if self.debug:
            if newfile is not None:
                print('shlex: pushing to file %s' % (self.infile,))
            else:
                print('shlex: pushing to stream %s' % (self.instream,))

    def pop_source(self):
        "Pop the input source stack."
        self.instream.close()
        (self.infile, self.instream, self.lineno) = self.filestack.popleft()
        if self.debug:
            print('shlex: popping to %s, line %d' \
                  % (self.instream, self.lineno))
        self.state = ' '

    def get_token(self):
        "Get a token from the input stream (or from stack if it's nonempty)"
        if self.pushback:
            tok = self.pushback.popleft()
            if self.debug >= 1:
                print("shlex: popping token " + repr(tok))
            return tok
        # No pushback.  Get a token.
        raw = self.read_token()
        # Handle inclusions
        if self.source is not None:
            while raw == self.source:
                spec = self.sourcehook(self.read_token())
                if spec:
                    (newfile, newstream) = spec
                    self.push_source(newstream, newfile)
                raw = self.get_token()
        # Maybe we got EOF instead?
        while raw == self.eof:
            if not self.filestack:
                return self.eof
            else:
                self.pop_source()
                raw = self.get_token()
        # Neither inclusion nor EOF
        if self.debug >= 1:
            if raw != self.eof:
                print("shlex: token=" + repr(raw))
            else:
                print("shlex: token=EOF")
        return raw

    def read_token(self):
        quoted = False
        escapedstate = ' '
        while True:
            if self.punctuation_chars and self._pushback_chars:
                nextchar = self._pushback_chars.pop()
            else:
                nextchar = self.instream.read(1)
            if nextchar == '\n' and self.state != 'a':
                self.lineno += 1
                if self.debug == 69:
                    print('shlex(144): LINE += 1 => %d' % self.lineno)
            if self.debug >= 3:
                print("shlex: in state %r I see character: %r" % (self.state,
                                                                  nextchar))
            if self.state is None:
                self.token = ''        # past end of file
                break
            elif self.state == ' ':
                if not nextchar:
                    self.state = None  # end of file
                    break
                elif nextchar in self.whitespace:
                    if self.debug >= 2:
                        print("shlex: I see whitespace in whitespace state")
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.__handle_comment(nextchar)
                    break
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif nextchar in self.wordchars:
                    self.token = nextchar
                    self.state = 'a'
                elif nextchar in self.punctuation_chars:
                    self.token = nextchar
                    self.state = 'c'
                elif nextchar in self.quotes:
                    if not self.posix:
                        self.token = nextchar
                    self.state = nextchar
                elif self.whitespace_split:
                    self.token = nextchar
                    self.state = 'a'
                else:
                    self.token = nextchar
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
            elif self.state in self.quotes:
                quoted = True
                if not nextchar:      # end of file
                    if self.debug >= 2:
                        print("shlex: I see EOF in quotes state")
                    # XXX what error should be raised here?
                    raise ValueError("No closing quotation")
                if nextchar == self.state:
                    if not self.posix:
                        self.token += nextchar
                        self.state = ' '
                        break
                    else:
                        self.state = 'a'
                elif (self.posix and nextchar in self.escape and self.state
                      in self.escapedquotes):
                    escapedstate = self.state
                    self.state = nextchar
                else:
                    self.token += nextchar
            elif self.state in self.escape:
                if not nextchar:      # end of file
                    if self.debug >= 2:
                        print("shlex: I see EOF in escape state")
                    # XXX what error should be raised here?
                    raise ValueError("No escaped character")
                # In posix shells, only the quote itself or the escape
                # character may be escaped within quotes.
                if (escapedstate in self.quotes and
                        nextchar != self.state and nextchar != escapedstate):
                    self.token += self.state
                self.token += nextchar
                self.state = escapedstate
            elif self.state in ('a', 'c'):
                if not nextchar:
                    self.state = None   # end of file
                    break
                elif nextchar in self.whitespace:
                    if self.debug >= 2:
                        print("shlex: I see whitespace in word state")
                    self.state = ' '
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
                elif nextchar in self.commenters:
                    self.__handle_comment(nextchar)
                    break
                elif self.state == 'c':
                    if nextchar in self.punctuation_chars:
                        self.token += nextchar
                    else:
                        if nextchar not in self.whitespace:
                            self._pushback_chars.append(nextchar)
                        self.state = ' '
                        break
                elif self.posix and nextchar in self.quotes:
                    self.state = nextchar
                elif self.posix and nextchar in self.escape:
                    escapedstate = 'a'
                    self.state = nextchar
                elif (nextchar in self.wordchars or nextchar in self.quotes
                      or (self.whitespace_split and
                          nextchar not in self.punctuation_chars)):
                    self.token += nextchar
                else:
                    if self.punctuation_chars:
                        self._pushback_chars.append(nextchar)
                    else:
                        self.pushback.appendleft(nextchar)
                    if self.debug >= 2:
                        print("shlex: I see punctuation in word state")
                    self.state = ' '
                    if self.token or (self.posix and quoted):
                        break   # emit current token
                    else:
                        continue
        result = self.token
        self.token = ''
        if self.posix and not quoted and result == '':
            result = None
        if self.debug > 1:
            if result:
                print("shlex: raw token=" + repr(result))
            else:
                print("shlex: raw token=EOF")
        return result

    # XXX: i still don't know how this works
    # but at least now i know it consumes a whole line and
    # propogates the line counter :D
    def __handle_comment(self, nextchar):
        self.token = nextchar
        self.state = ' '
        comment = self.instream.readline()
        logger.debug('COMMENT YIPEE %r', comment)
        logger.debug('CURRENT TOKEN IS A %r', self.token)
        logger.debug('LINENO = %d, PUSHBACK = %r',
                     self.lineno, self._pushback_chars)
        self.lineno += 1

    def sourcehook(self, newfile):
        "Hook called on a filename to be sourced."
        if newfile[0] == '"':
            newfile = newfile[1:-1]
        # This implements cpp-like semantics for relative-path inclusion.
        if isinstance(self.infile, str) and not os.path.isabs(newfile):
            newfile = os.path.join(os.path.dirname(self.infile), newfile)
        return (newfile, open(newfile, "r"))

    def error_leader(self, infile=None, lineno=None):
        "Emit a C-compiler-like, Emacs-friendly error-message leader."
        if infile is None:
            infile = self.infile
        if lineno is None:
            lineno = self.lineno
        return "\"%s\", line %d: " % (infile, lineno)

    def __iter__(self):
        return self

    def __next__(self):
        token = self.get_token()
        if token == self.eof:
            raise StopIteration
        return token
