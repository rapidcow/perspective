"""Convert plain format into JSONLoader/EELoader entries"""
__all__ = ['Error', 'PlainEntryConverter']

from collections import OrderedDict as ODict
import datetime
import re

# Panel keys
DATE_KEY = 'date'
RATING_KEY = 'rating'
ENTRY_KEY = 'entries'
# Entry keys
DATA_KEY = 'data'
DATE_TIME_KEY = 'date-time'
TIME_KEY = 'time'
INSIGHT_KEY = 'insight'
TYPE_KEY = 'type'
TRACK_KEY = 'tracks'
# Now Then Track keys
START_KEY = 'start'
END_KEY = 'end'
# EELoader format
ENTRIES_KEY = 'entries'
RATINGS_KEY = 'ratings'

PARGS_DELIM = ETIME_DELIM = re.compile(r'[\s,]+')
EARGS_INSIGHT = re.compile(r'\s*INSIGHT\s+', flags=re.IGNORECASE)
EARGS_ENTRY = re.compile(r'\s*ENTRY\s+', flags=re.IGNORECASE)
EARGS_DELIM = re.compile(r'\s*,\s*')
# to make it simpler we will not make it consume whitespace >->
EARGS_INTVL = re.compile(r'(?:-|to)')


class Error(ValueError):
    def __init__(self, s, lineno):
        super().__init__(f'line {lineno}: {s}')


def split_line(line):
    try:
        kw, args = line.split(maxsplit=1)
    except ValueError:
        return line.strip().upper(), ''
    return kw.upper(), args


def split_time(s):
    chunks = ETIME_DELIM.split(s)
    result = []
    for chunk in chunks:
        if result and chunk.upper() in {'AM', 'PM'}:
            result[-1] += ' ' + chunk
        else:
            result.append(chunk)
    return result


MONTHS = [
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
]
WDAYS = [
    'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
]
WDAYS_FULL = [
    'Monday', 'Tuesday', 'Wednesday', 'Thursday',
    'Friday', 'Saturday', 'Sunday',
]

def parse_month_day(m, d, y, wd=None):
    m = m.lower()
    for mm, month in enumerate(MONTHS, start=1):
        if m.startswith(month):
            break
    else:
        raise ValueError(f'invalid month: {m!r}')

    date_obj = datetime.date(y, mm, d)
    if wd is not None:
        wd_exp = date_obj.weekday()
        if wd != wd_exp:
            raise ValueError(f'date {date_obj} should be on '
                             f'{WDAYS_FULL[wd_exp]}, not {WDAYS_FULL[wd]}')
    return date_obj


def parse_weekday(w):
    w = w.lower()
    for wd, weekday in enumerate(WDAYS):
        if w.startswith(weekday):
            return wd
    raise ValueError(f'invalid weekday: {w!r}')


def parse_time(t):
    try:
        return datetime.time.fromisoformat(t)
    except ValueError:
        time_formats = ['%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%z %p']
        for time_fmt in time_formats:
            try:
                return datetime.datetime.strptime(t, time_fmt).timetz()
            except ValueError:
                pass
        raise ValueError(f'invalid time: {t!r}')


def format_date(d):
    # return d.strftime('%a %b %d %Y')
    return d.strftime('%Y-%m-%d')


def format_time(t, d):
    timespec = 'auto' if t.second or t.microsecond else 'minutes'
    if t.date() == d:
        return 'time', t.timetz().isoformat(timespec)
    # d_str = t.strftime('%a %b %d {} %Y')
    d_str = t.strftime('%Y-%m-%d {}')
    return 'date-time', d_str.format(t.timetz().isoformat(timespec))


class PlainEntryConverter:
    __slots__ = ('year', 'lyear')

    def __init__(self, year):
        self.year = self.lyear = year

    def convert(self, fp):
        lineno = 0
        panels = []
        panel = None

        for line in fp:
            lineno += 1
            kw, args = split_line(line)
            if kw == 'DATE':
                try:
                    panel = self.make_panel(args)
                except Exception as exc:
                    raise Error('failed to make pael', lineno) from exc
                panels.append(panel)
                self.lyear = panel[DATE_KEY].year
            elif kw in {'INSIGHT', 'ENTRY', 'TIME'}:
                if panel is None:
                    raise Error('No known panel', lineno)
                is_insight = False
                if kw == 'INSIGHT':
                    # remove the 'ENTRY' string potentially following
                    # 'INSIGHT'
                    m = EARGS_ENTRY.match(args)
                    if m:
                        args = args[m.end():]
                    is_insight = True
                else:
                    m = EARGS_INSIGHT.match(args)
                    if m:
                        args = args[m:end():]
                        is_insight = True
                try:
                    entry = self.make_entry(panel, args, is_insight)
                except Exception as exc:
                    raise Error('failed to make entry', lineno) from exc
                entry_list = panel[ENTRY_KEY]
                entry_list.append(entry)

                while True:
                    try:
                        line = next(fp)
                        lineno += 1
                    except StopIteration:
                        raise Error('EOF while searching for BEGIN', lineno)
                    kw, args = split_line(line)
                    if kw == 'BEGIN':
                        break
                    if self.is_nonempty(line):
                        raise Error('Expected BEGIN', lineno)

                # Append the entry type
                args = args.strip()
                if args:
                    entry[TYPE_KEY] = args
                    entry.move_to_end(DATA_KEY)
                    if TRACK_KEY in entry:
                        entry.move_to_end(TRACK_KEY)

                data = entry[DATA_KEY]
                while True:
                    try:
                        line = next(fp)
                    except StopIteration:
                        raise Error('EOF while scanning for END',
                                    lineno) from None
                    lineno += 1
                    kw, args = split_line(line)
                    if kw == 'END' and not args.strip():
                        break
                    elif kw.startswith('END!'):
                        line = line.replace('END!', 'END', 1)
                    data.append(line)

                self.prune_data(data)
                entry[DATA_KEY] = ''.join(data).strip('\n')
            elif self.is_nonempty(line):
                raise Error('Invalid line', lineno)

        for panel in panels:
            panel[DATE_KEY] = format_date(panel[DATE_KEY])

        return panels

    def convert_ii(self, fp):
        panels = self.convert(fp)
        entries = []
        ratings = ODict()
        for panel in panels:
            date_str = panel[DATE_KEY]
            if RATING_KEY in panel:
                ratings[date_str] = panel[RATING_KEY]
            first = True
            for entry in panel[ENTRY_KEY]:
                new_entry = ODict()
                if first:
                    new_entry[DATE_KEY] = date_str
                new_entry.update(entry)
                entries.append(new_entry)
                first = False
        return ODict([
            (ENTRIES_KEY, entries),
            (RATINGS_KEY, ratings)
        ])

    def is_nonempty(self, line):
        return line.strip() and not line.lstrip().startswith('#')

    def make_panel(self, args):
        # reset the local year var for context
        self.lyear = self.year
        p_date, rating = self.parse_panel_args(args)
        panel = ODict()
        panel[DATE_KEY] = p_date
        if rating is not None:
            panel[RATING_KEY] = rating
        panel[ENTRY_KEY] = []
        return panel

    def make_entry(self, panel, args, is_insight):
        p_date = panel[DATE_KEY]
        time_key, time, tracks = self.parse_entry_args(p_date, args)
        entry = ODict()
        entry[time_key] = time
        if is_insight:
            entry[INSIGHT_KEY] = True
        entry[DATA_KEY] = []
        if tracks:
            entry[TRACK_KEY] = tracks
        return entry

    def parse_panel_args(self, args):
        chunks = PARGS_DELIM.split(args)
        if chunks and not chunks[0]:
            del chunks[0]
        if chunks and not chunks[-1]:
            del chunks[-1]
        try:
            return self.parse_panel_date(chunks), None
        except ValueError:
            try:
                return self.parse_panel_date(chunks[:-1]), chunks[-1]
            except ValueError:
                raise ValueError(f'invalid DATE string: {args!r}')

    def parse_panel_date(self, chunks):
        n = len(chunks)
        if n == 2:
            # Month + day
            month, day = chunks
            return parse_month_day(month, int(day), self.lyear)
        elif n == 3:
            a, b, c = chunks
            # Weekday + month + day
            try:
                wd = parse_weekday(a)
                return parse_month_day(b, int(c), self.lyear, wd=wd)
            except ValueError:
                # Month + day + year
                return parse_month_day(a, int(b), int(c))
        elif n == 4:
            # Weekday + month + day + year
            a, b, c, d = chunks
            wd = parse_weekday(a)
            return parse_month_day(b, int(c), int(d), wd=wd)
        raise ValueError(f'failed with chunks: {chunks!r}')

    # 'p_date' is a datetime.date object,
    # 'e_time' is a (naive) datetime.datetime object while
    # 'time' is just a str representation of it
    def parse_entry_args(self, p_date, args):
        # split by commas and ignore empty items
        args = [s for s in EARGS_DELIM.split(args) if s]
        if not args:
            raise ValueError('expected at least one argument for ENTRY')
        tracks = []
        arg = args[0].strip()
        if EARGS_INTVL.search(arg):
            start, end = EARGS_INTVL.split(arg)
            e_time = self.parse_entry_time(start.strip(), p_date)
            e_date = e_time.date()
            start_t, end_t = self.parse_entry_interval(
                e_time, start.strip(), end.strip())
            time_key, time = format_time(start_t, p_date)
            event = ODict([
                (START_KEY, format_time(start_t, e_date)[1]),
                (END_KEY, format_time(end_t, e_date)[1]),
            ])
            tracks.append(event)
        else:
            e_time = self.parse_entry_time(arg, p_date)
            time_key, time = format_time(e_time, p_date)

        for arg in args[1:]:
            arg = arg.strip()
            if EARGS_INTVL.search(arg):
                start, end = EARGS_INTVL.split(arg)
                start_t, end_t = self.parse_entry_interval(
                    e_time, start.strip(), end.strip())
                event = ODict([
                    (START_KEY, format_time(start_t, e_date)[1]),
                    (END_KEY, format_time(end_t, e_date)[1]),
                ])
                tracks.append(event)
            else:
                raise ValueError(f'expected an interval, got {arg!r}')
        return time_key, time, tracks

    # infers date from ref_date if possible (this method is used by
    # both parse_entry_args() and parse_entry_interval())
    def parse_entry_time(self, time_str, ref_date):
        try:
            time_val = parse_time(time_str)
            return datetime.datetime.combine(ref_date, time_val)
        except ValueError:
            pass

        chunks = split_time(time_str)
        if chunks and not chunks[0]:
            del chunks[0]
        if chunks and not chunks[-1]:
            del chunks[-1]
        n = len(chunks)
        if n == 3:
            m, d, t = chunks
            date_val = self.parse_panel_date([m, d])
            time_val = parse_time(t)
        elif n == 4:
            # Weekday month day time
            try:
                wd, m, d, t = chunks
                date_val = self.parse_panel_date([wd, m, d])
                time_val = parse_time(t)
            except ValueError:
                # Month day time year
                m, d, t, y = chunks
                date_val = self.parse_panel_date([m, d, y])
                time_val = parse_time(t)
        elif n == 5:
            # Weekday month day time year
            wd, m, d, t, y = chunks
            date_val = self.parse_panel_date([wd, m, d, y])
            time_val = parse_time(t)
        else:
            raise ValueError(f'invalid entry time string: {time_str!r}')
        return datetime.datetime.combine(date_val, time_val)

    def parse_entry_interval(self, e_time, start, end):
        e_date = e_time.date()
        start_t = self.parse_entry_time(start, e_date)
        try:
            end_m = int(end)
            return start_t, start_t.replace(minute=end_m)
        except ValueError:
            pass
        end_t = self.parse_entry_time(end, start_t.date())
        return start_t, end_t

    def prune_data(self, data):
        for i, line in enumerate(data):
            if line.rstrip('\n'):
                break
        del data[:i]
        data.reverse()

        for i, line in enumerate(data):
            if line.rstrip('\n'):
                break
        del data[:i]
        data.reverse()

        # remove spurious whitespace
        # for i, line in enumerate(data):
        #     data[i] = line.rstrip('\n').rstrip() + '\n'


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs='?', default=None)
    # entry format
    parser.add_argument('--format', '-f', dest='fmt', type=int, default=1)
    # default year
    parser.add_argument('--year', '-y', type=int,
                        default=datetime.date.today().year)
    args = parser.parse_args()
    conv = 'convert' if args.fmt == 1 else 'convert_ii'
    if args.infile is not None:
        with open(args.infile) as fp:
            data = getattr(PlainEntryConverter(args.year), conv)(fp)
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        import sys
        data = getattr(PlainEntryConverter(args.year), conv)(sys.stdin)
        print(json.dumps(data, indent=2, ensure_ascii=False))
