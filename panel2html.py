"""Export panels to HTML.  Something I wrote personally to compensate
for the lack of images from the terminal output...

This script relies on 2 external packages you should install using
pip in advance:

*  beautifulsoup4 (for hacky HTML; see replace_url())
*  tqdm (fancy progress bar; it doesn't take long to install it
   so I just put it here as a requirement XD)

There are 2 packages that are OPTIONAL for converting HEIF images:

*  pyheif (Python interface to libheif which can be hard to install)
*  PIL (used along with pyheif)

And of course, you should install my psp package too. ;)

Also also, if you want to produce cool Markdown/LaTeX entries,
make sure pandoc and a (La)TeX distribution are installed on your
device.  Hopefully you'll find these links helpful:

*  pandoc: https://pandoc.org/
*  LaTeX: https://www.latex-project.org/get/
"""

import collections
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse

import bs4

# Optional packages
try:
    import pyheif
except ImportError:
    pyheif = None

try:
    from PIL import Image
except ImportError:
    Image = None

import psp.timeutil
import psp.util
import psp.filetypes
from psp.stringify import PanelFormatter, EntryFormatter
from psp.serializers.json import JSONLoader, JSONDumper
from psp.ext.bigentry import BigEntry
from psp.ext.captions import CaptionEntry
from psp.ext.metadata import MetaEntry
import tqdm

__all__ = ['write_panel_html', 'export_panels']

# Configuration
time_format = '24 hour'
default_filename = 'file'

MATHJAX_URL = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js'

TEMPLATE = """<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <title>{TITLE}</title>
  <link rel="stylesheet" href="{CSS}" />
  <script type="text/javascript" id="MathJax-script" async
    src="{MATHJAX}">
  </script>
</head>

<header>
  <div class="header">
{HEADER}
  </div>
</header>

<body>
  <div class="row">
    <div class="leftcolumn">
{LEFT}
    </div>
    <div class="rightcolumn">
{RIGHT}
    </div>
  </div>
</body>

<footer>
  <div class="footer">
    <h2>Footer</h2>
  </div>
</footer>
</html>
"""

STYLESHEET = """body {
  font-family: "SF Mono", "Ubuntu Mono", Courier, monospace;
  padding: 20px;
  background: #f1f1f1;
}

.header {
  padding: 30px;
  font-size: 30px;
  text-align: center;
  background: white;
}

/* Create two unequal columns that float next to each other */

.leftcolumn {
  float: left;
  width: 74%;
}

.rightcolumn {
  float: left;
  width: 24%;
  padding-left: 20px;
}

img, video {
  padding: 0 3ex 0 3ex;
  width: 80%;
  /* Centering */
  display: block;
  margin: 0 auto;
}

figcaption {
  margin-top: 1ex;
}

pre {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 1rem;
  padding: 0.25rem 0 0.25rem 2em;
  /* background-color: #f6f6f6; */
}

pre.no-bg {
  padding: 0;
  background-color: inherit;
}

code {
  font-family: inherit;
  font-size: 0.85rem;
  background-color: #f6f6f6;
  padding: 3px;
  margin: 3px 0;
}

pre code {
  font-size: inherit;
  background-color: inherit;
  padding: 0;
  margin: 0;
}

/* Add a card effect for articles */
.card {
  background-color: white;
  padding: 20px;
  margin-top: 20px;
}

/* Attributes inside cards */
.card-attr {
  font-weight: bold;
  font-size: 16px;
  margin: 0.3ex 0 1.2ex 0;
  padding-left: 2em;
}

/* First paragraph in card-attr?? (> for targetting immediate
 * child element) */
.card-attr > p:first-of-type {
  /* Hanging indent trick */
  text-indent: -2em;
}

/* Insight card */
.insight {
  color: RoyalBlue;
}

.row:after {
  content: "";
  display: table;
  clear: both;
}

.footer {
  padding: 20px;
  text-align: center;
  background: #ddd;
  margin-top: 20px;
}

.sourceCode {
  color: black;
}

/* nasty hacks: https://css-tricks.com/two-issues-styling-the-details-element-and-how-to-solve-them/ */
details > summary:first-of-type {
  cursor: pointer;
}

details > summary:first-of-type > * {
  display: inline;
}

/* Copied from pandoc */
pre > code.sourceCode { white-space: pre; position: relative; }
pre > code.sourceCode > span { display: inline-block; line-height: 1.25; }
pre > code.sourceCode > span:empty { height: 1.2em; }
.sourceCode { overflow: visible; }
code.sourceCode > span { color: inherit; text-decoration: inherit; }
div.sourceCode { margin: 1em 0; }
pre.sourceCode { margin: 0; }
@media screen {
div.sourceCode { overflow: auto; }
}
@media print {
pre > code.sourceCode { white-space: pre-wrap; }
pre > code.sourceCode > span { text-indent: -5em; padding-left: 5em; }
}
pre.numberSource code
  { counter-reset: source-line 0; }
pre.numberSource code > span
  { position: relative; left: -4em; counter-increment: source-line; }
pre.numberSource code > span > a:first-child::before
  { content: counter(source-line);
    position: relative; left: -1em; text-align: right; vertical-align: baseline;
    border: none; display: inline-block;
    -webkit-touch-callout: none; -webkit-user-select: none;
    -khtml-user-select: none; -moz-user-select: none;
    -ms-user-select: none; user-select: none;
    padding: 0 4px; width: 4em;
    color: #aaaaaa;
  }
pre.numberSource { margin-left: 3em; border-left: 1px solid #aaaaaa; \
padding-left: 4px; }
div.sourceCode
  {   }
@media screen {
pre > code.sourceCode > span > a:first-child::before { \
text-decoration: underline; }
}
code span.al { color: #ff0000; font-weight: bold; } /* Alert */
code span.an { color: #60a0b0; font-weight: bold; font-style: italic; } \
/* Annotation */
code span.at { color: #7d9029; } /* Attribute */
code span.bn { color: #40a070; } /* BaseN */
code span.bu { } /* BuiltIn */
code span.cf { color: #007020; font-weight: bold; } /* ControlFlow */
code span.ch { color: #4070a0; } /* Char */
code span.cn { color: #880000; } /* Constant */
code span.co { color: #60a0b0; font-style: italic; } /* Comment */
code span.cv { color: #60a0b0; font-weight: bold; font-style: italic; } \
/* CommentVar */
code span.do { color: #ba2121; font-style: italic; } /* Documentation */
code span.dt { color: #902000; } /* DataType */
code span.dv { color: #40a070; } /* DecVal */
code span.er { color: #ff0000; font-weight: bold; } /* Error */
code span.ex { } /* Extension */
code span.fl { color: #40a070; } /* Float */
code span.fu { color: #06287e; } /* Function */
code span.im { } /* Import */
code span.in { color: #60a0b0; font-weight: bold; font-style: italic; } \
/* Information */
code span.kw { color: #007020; font-weight: bold; } /* Keyword */
code span.op { color: #666666; } /* Operator */
code span.ot { color: #007020; } /* Other */
code span.pp { color: #bc7a00; } /* Preprocessor */
code span.sc { color: #4070a0; } /* SpecialChar */
code span.ss { color: #bb6688; } /* SpecialString */
code span.st { color: #4070a0; } /* String */
code span.va { color: #19177c; } /* Variable */
code span.vs { color: #4070a0; } /* VerbatimString */
code span.wa { color: #60a0b0; font-weight: bold; font-style: italic; } \
/* Warning */
"""

INSIGHT_CARD = """<div class="card insight"><h1>Insights</h1></div>"""

_TYPE2EXT = {
    'png': '.png',
    'jpeg': '.jpg',
    'mp4': '.mp4',
    'ogg': '.ogg',
    'webm': '.webm',
    'mp3': '.mp3',
    'aac': '.aac',
}

UTC = datetime.timezone.utc


def get_meta_attribute(entry, name, default):
    if isinstance(entry, MetaEntry):
        return entry.get_meta_attribute(name, default)
    return default


def get_rating(panel):
    if panel.has_rating():
        return panel.get_rating()
    return None


def get_question(entry):
    if entry.has_question():
        return entry.get_question()
    return ''

def get_caption(entry):
    if isinstance(entry, CaptionEntry) and entry.has_caption():
        return entry.get_caption()
    return ''


def get_transcription(entry):
    if isinstance(entry, CaptionEntry) and entry.has_transcription():
        return entry.get_transcription()
    return ''


def has_title(entry):
    return isinstance(entry, CaptionEntry) and entry.has_title()


def get_title(entry):
    return entry.get_title()


def export_entry(entry, filepath):
    with open(filepath, 'xb') as fdst:
        with entry.stream_raw_data() as fsrc:
            shutil.copyfileobj(fsrc, fdst)


def write_panel_html(panel, dirpath, filename='index.html', *,
                     time_zone=None, sidebar_extra='', encoding='utf-8',
                     css=None, mathjax=None):
    """Export a panel to an HTML file inside the directory 'dirpath'."""
    panel_title = panel.date.strftime('%A, %B %e, %Y')
    rating = get_rating(panel)
    if rating is not None:
        panel_title += ' ' + str(rating)
    title_html = f'<h2>{panel_title}</h2>'

    # Split into main and insight entries
    main_entries = []
    insight_entries = []
    for entry in panel.entries():
        if entry.insight:
            insight_entries.append(entry)
        else:
            main_entries.append(entry)
    main_entries.sort(key=lambda e: e.time.astimezone(UTC))
    insight_entries.sort(key=lambda e: e.time.astimezone(UTC))

    # See if the panel has a common time zone
    if panel.has_entries():
        entries = panel.entries()
        first = next(entries).time
        if all(e.time.tzinfo == first.tzinfo or
               e.time.utcoffset() == first.utcoffset()
               for e in entries):
            time_zone = first.tzinfo

    entries_html_parts = []
    dircount = 0
    dircount = add_entries(entries_html_parts, main_entries, dirpath,
                           dircount, '<div class="card">', '</div>',
                           time_zone)
    if insight_entries:
        entries_html_parts.append(INSIGHT_CARD)
    dircount = add_entries(entries_html_parts, insight_entries, dirpath,
                           dircount, '<div class="insight card">', '</div>',
                           time_zone)
    no_entries_card = '<div class="card"><p>no entries...</p></div>'
    entries_html = ''.join(entries_html_parts).rstrip('\n') or no_entries_card

    sidebar = get_status_html(panel, time_zone) + sidebar_extra
    text = TEMPLATE.format(TITLE=panel_title, HEADER=title_html,
                           LEFT=entries_html, RIGHT=sidebar,
                           CSS=html.escape(css or 'stylesheet.css'),
                           MATHJAX=html.escape(mathjax or MATHJAX_URL))
    with open(os.path.join(dirpath, filename), 'x',
              encoding=encoding) as fp:
        fp.write(text)
    if css is None:
        with open(os.path.join(dirpath, 'stylesheet.css'), 'x',
                  encoding=encoding) as fp:
            fp.write(STYLESHEET)


def add_entries(parts, entries, parent_dir, dircount, lefttag, righttag,
                time_zone):
    relpath = str(dircount)
    dirpath = os.path.join(parent_dir, relpath)
    for entry in entries:
        parts.append(lefttag)
        parts.append('\n')
        parts.append(get_entry_html(entry, dirpath, relpath, time_zone))
        parts.append(righttag)
        parts.append('\n')
        # Only advance directory count if we exported something
        if os.path.exists(dirpath):
            dircount += 1
            relpath = str(dircount)
            dirpath = os.path.join(parent_dir, relpath)
    return dircount


def get_entry_html(entry, dirpath, relpath, time_zone):
    """Get the entry 'entry' as an HTML div element, unpacking
    content to 'dirpath' when necessary.  ('relpath' is used for
    links inside the HTML file.)
    """
    entry_type = entry.get_type()
    entry_format = entry.get_format()
    # For text types that can reference other files (such as Markdown),
    # we will have to do something nasty to change those relative links
    # so that they point to the new directory 'dirpath'...
    if isinstance(entry, BigEntry):
        file_type = entry.get_main_file_type()
        file_format = entry.get_main_file_format()
        if file_type == 'html':
            content = sanitize_html(entry, dirpath, relpath, time_zone)
        elif file_type == 'markdown':
            content = markdown_to_html(entry, dirpath, relpath, time_zone)
        elif file_type == 'tex':
            content = tex_to_html(entry, dirpath, relpath, time_zone)
        elif file_type == 'plain':
            content = plain_to_html(entry, time_zone)
        else:
            raise ValueError(f'unsupported bigentry file type: '
                             f'{file_type!r}')
        if content is not None:
            return content
    if entry.is_text():
        if entry_type == 'markdown':
            content = markdown_to_html(entry, dirpath, relpath, time_zone)
            if content is not None:
                return content
        # Fallback
        parts = []
        entry_head(parts, entry, time_zone)
        parts.append('<pre class="no-bg">')
        parts.append(html.escape(get_entry_text(entry)))
        parts.append('</pre>\n')
        entry_tail(parts, entry, time_zone)
        return ''.join(parts)
    if (entry_type in {'png', 'jpeg'}
            or entry_type == 'heif' and can_convert_heif(entry)):
        os.mkdir(dirpath)
        basename = get_basename(entry, default='image')
        if entry_type == 'heif':
            ext = '.jpg'
            filename = basename + ext
            target = heif_to_jpg(entry, os.path.join(dirpath, filename))
        else:
            ext = _TYPE2EXT[entry_type]
            filename = basename + ext
            export_entry(entry, os.path.join(dirpath, filename))
        parts = []
        entry_head(parts, entry, time_zone)
        parts.append('<img')
        caption = get_caption(entry)
        if caption:
            parts.append(f' alt="{html.escape(caption)}"')
        srcpath = html.escape(os.path.join(relpath, filename))
        parts.append(f' src="{srcpath}" />\n')
        entry_tail(parts, entry, time_zone)
        return ''.join(parts)
    # Audio
    if entry_type in {'mp3', 'aac'}:
        os.mkdir(dirpath)
        basename = get_basename(entry, default='audio')
        ext = _TYPE2EXT[entry_type]
        filename = basename + ext
        srcpath = html.escape(os.path.join(relpath, filename))
        export_entry(entry, os.path.join(dirpath, filename))
        parts = []
        entry_head(parts, entry, time_zone)
        parts.append('<audio controls')
        parts.append(f' src="{srcpath}">')
        parts.append('</audio>\n')
        entry_tail(parts, entry, time_zone)
        return ''.join(parts)
    # Videos
    if entry_type in {'mp4', 'ogg', 'webm'}:
        os.mkdir(dirpath)
        basename = get_basename(entry, default='video')
        ext = _TYPE2EXT[entry_type]
        filename = basename + ext
        srcpath = html.escape(os.path.join(relpath, filename))
        export_entry(entry, os.path.join(dirpath, filename))
        parts = []
        entry_head(parts, entry, time_zone)
        parts.append('<video controls>\n')
        parts.append(f'  <source src={srcpath}>')
        parts.append('</video>\n')
        entry_tail(parts, entry, time_zone)
        return ''.join(parts)
    # Default scenario for a file
    parts = []
    entry_head(parts, entry, time_zone)
    try:
        ext = _TYPE2EXT[entry_type]
    except KeyError:
        ctx = psp.filetypes.get_context()
        try:
            ext = ctx.get_default_extension(entry_type)
        except LookupError:
            ext = ''
    basename = get_basename(entry, default='something')
    filename = basename + ext
    filepath = os.path.join(dirpath, filename)
    os.mkdir(dirpath)
    export_entry(entry, filepath)
    src = html.escape(os.path.join(relpath, filename))
    parts.append(f'<a href="{src}">'
                 f'<pre class="no-bg">'
                 f'{html.escape(filename, quote=False)}'
                 f'</pre></a>\n')
    entry_tail(parts, entry, time_zone)
    return ''.join(parts)


def get_status_html(panel, time_zone):
    """Get the status of the panel 'panel' as an HTML div element."""
    entry_count = sum(1 for e in panel.entries())
    utcnow = datetime.datetime.utcnow().ctime()
    return (f'<div class="card">\n'
            f'<p>Entries: {entry_count}</p>\n'
            f'<p>Time zone: {time_zone}</p>\n'
            f'<p>Exported at: {utcnow} (UTC)</p>\n'
            f'</div>')


# The real work
def entry_head(parts, entry, time_zone):
    # global time_format    # not really needed since
                            # we're not mutating) it
    title = (EntryFormatter(time_format=time_format, time_zone=time_zone)
             .get_title(entry.panel.date, entry.time))
    parts.append('<h2>')
    parts.append(html.escape(title).replace('  ', ' &nbsp;'))
    parts.append('</h2>\n')
    attrs = []

    question = get_question(entry)
    if question:
        attrs.append(('Question', question))

    ent_type = entry.get_type()
    if ent_type not in {'plain', 'binary'}:
        if isinstance(entry, BigEntry):
            type_str = (f'big entry (archive type {ent_type}, '
                        f'main file type {entry.get_main_file_type()})')
            attrs.append(('Type', type_str))
        else:
            attrs.append(('Type', ent_type))

    try:
        meta = entry.get_meta_attributes()
    except AttributeError:
        meta = {}

    desc = meta.pop('desc', '')
    if desc:
        attrs.append(('Description', desc))

    created = meta.pop('created', None)
    if created is not None:
        attrs.append(('Created', str(created)))

    modified = meta.pop('modified', None)
    if modified is not None:
        attrs.append(('Modified', str(modified)))

    posted = meta.pop('posted', None)
    if posted is not None and posted != entry.time:
        attrs.append(('Posted', str(posted)))

    caption = get_caption(entry)
    if caption:
        attrs.append(('Caption', caption))

    tr = get_transcription(entry)
    if tr:
        attrs.append(('Transcription', tr))

    hide = meta.pop('hide', False)
    if hide:
        parts.append('<details>\n')
        if not isinstance(hide, bool):
            parts.append('<summary>')
            parts.append(convert_markdown(hide) or html.escape(hide))
            parts.append('</summary>\n')
        else:
            parts.append('<summary>Here lies a mysterious hidden '
                         'entry...</summary>\n')

    # ignore empty tags (DON'T put this out there!)
    if 'tags' in meta and not meta['tags']:
        meta.pop('tags')

    for key, value in meta.items():
        attrs.append((key, repr(value)))

    for term, value in attrs:
        parts.append('<div class="card-attr">\n')
        # Only un-hide the HTML comments i guess
        value = value.replace('<!--', '&lt;!--').replace('-->', '--&gt;')
        # parts.append('  <pre class="no-bg">')
        # parts.append(term + ': ')
        # parts.append(html.escape(value))
        # parts.append('</pre>\n')
        content = (convert_markdown(f'{term}: {value}') or
                   html.escape(f'{term}: {value}'))
        parts.append(replace_stuff_for_monospace(content))
        parts.append('</div>\n')

    if has_title(entry):
        parts.append('<hr />')
        parts.append('<h1 class="title">')
        parts.append(html.escape(get_title(entry)))
        parts.append('</h1>\n')


def entry_tail(parts, entry, time_zone):
    if get_meta_attribute(entry, 'hide', False):
        parts.append('</details>\n')


def get_entry_text(entry):
    return replace_stuff_for_monospace(entry.get_data())


def replace_stuff_for_monospace(text):
    # U+2026: horizontal ellipsis
    # U+2013: en dash
    # U+2014: em dash
    return (text.replace('\u2026', '...').replace('\u2013', '--')
            .replace('\u2014', '---'))


def plain_to_html(entry, time_zone):
    parts = []
    entry_head(parts, entry, time_zone)
    parts.append('<pre class="no-bg">\n')
    parts.append(html.escape(get_entry_text(entry)))
    parts.append('</pre>')
    entry_tail(parts, entry, time_zone)
    return ''.join(parts)


def sanitize_html(entry, dirpath, relpath, time_zone):
    parts = []
    entry_head(parts, entry, time_zone)
    if isinstance(entry, BigEntry):
        entry.extract_all(dirpath)
        os.unlink(os.path.join(dirpath, entry.get_main_file()))
    doc = get_entry_text(entry)
    doc = replace_urls(doc, dirpath, relpath)
    parts.append(replace_stuff_for_monospace(doc))
    entry_tail(parts, entry, time_zone)
    return ''.join(parts)


def markdown_to_html(entry, dirpath, relpath, time_zone):
    pandoc_format = get_meta_attribute(entry, 'pandoc-format', 'markdown')
    # if entry.panel.date.timetuple()[:3] == (2023, 2, 13) and \
    #         entry.time.timetuple()[:5] == (2023, 2, 13, 20, 16):
    #     breakpoint()
    doc = convert_markdown(get_entry_text(entry), format=pandoc_format)
    if doc is None:
        return None

    parts = []
    entry_head(parts, entry, time_zone)
    if isinstance(entry, BigEntry):
        entry.extract_all(dirpath)
        os.unlink(os.path.join(dirpath, entry.get_main_file()))
    doc = replace_urls(doc, dirpath, relpath)
    parts.append(replace_stuff_for_monospace(doc))
    entry_tail(parts, entry, time_zone)
    return ''.join(parts)


# ONLY bigentry should call this
def tex_to_html(entry, dirpath, relpath, time_zone):
    if isinstance(entry, BigEntry):
        tex_format = entry.get_main_file_format()
    else:
        tex_format = entry.get_format()
    if tex_format is None:
        tex_format = 'pdftex'

    valid_formats = {
        'tex', 'latex', 'pdftex', 'pdflatex', 'xetex', 'xelatex',
        'luatex', 'lualatex', 'context',
    }
    if tex_format not in valid_formats:
        raise ValueError(f'invalid tex format: {tex_format!r}')

    if shutil.which(tex_format) is None:
        return

    parts = []
    entry_head(parts, entry, time_zone)

    with tempfile.TemporaryDirectory() as tmpdir:
        if isinstance(entry, BigEntry):
            entry.extract_all(tmpdir)
            filename = entry.get_main_file()
        else:
            raise ValueError('tex_to_html() should be called with a bigentry!')
        with tempfile.TemporaryDirectory() as outdir:
            engine = ('pdflatex' if tex_format == 'latex'
                      else 'pdftex' if tex_format == 'tex'
                      else tex_format)
            oldpwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                retval = subprocess.call(
                    [engine, '-shell-escape', '-output-directory',
                     outdir, filename],
                    stdout=subprocess.DEVNULL)
                if retval:
                    raise RuntimeError('error while compiling tex file')
            finally:
                os.chdir(oldpwd)
            pdf_name = None
            for ent in os.scandir(outdir):
                if ent.is_file() and ent.name.endswith('.pdf'):
                    pdf_name = ent.name
                    break
            if pdf_name is None:
                raise ValueError('cannot find output pdf')
            pdf_path = os.path.join(dirpath, pdf_name)
            os.mkdir(dirpath)
            shutil.copy(os.path.join(outdir, pdf_name), pdf_path)
            parts.append(f'<a href="'
                         f'{html.escape(os.path.join(relpath, pdf_name))}">'
                         f'<pre class="no-bg">'
                         f'{html.escape(pdf_name, quote=False)}</pre>'
                         f'</a>\n')

    if isinstance(entry, BigEntry):
        entry.extract_all(dirpath)
        os.unlink(os.path.join(dirpath, entry.get_main_file()))
    entry_tail(parts, entry, time_zone)
    return ''.join(parts)


def heif_to_jpg(entry, target):
    try:
        heif_file = pyheif.read(entry.get_data())
        im = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            'raw',
            heif_file.mode,
            heif_file.stride)
        im.save(target, format='jpeg')
        return target
    # this is supposed to just catch ffi.error but
    # i don't know how the fuck i am going to import
    # a C extension module
    except Exception:
        pass
    with tempfile.NamedTemporaryFile(
            suffix='.heif', delete=False) as file:
        with entry.stream_raw_data() as fp:
            shutil.copyfileobj(fp, file)
    try:
        subprocess.check_call(['convert', file.name, target],
                              # stdout=subprocess.DEVNULL,
                              # stderr=subprocess.DEVNULL,
                              )
    finally:
        os.unlink(file.name)


def can_convert_heif(entry):
    file = tempfile.NamedTemporaryFile(delete=False)
    file.close()
    try:
        heif_to_jpg(entry, file.name)
    except ValueError:
        return False
    finally:
        os.unlink(file.name)
    return True


def convert_markdown(doc, *, format='markdown'):
    """Convert markdown with pandoc"""
    if shutil.which('pandoc') is None:
        return None
    return subprocess.check_output(
        ['pandoc', '--from', format, '--to', 'html', '--mathjax'],
        input=doc, text=True)


def get_basename(entry, default=default_filename):
    filename = get_meta_attribute(entry, 'filename', None)
    e_type = entry.get_type()
    if filename is None:
        if entry.has_source():
            filename = os.path.basename(entry.get_source())
        else:
            return default
    ctx = psp.filetypes.get_context()
    if ctx.has_type(e_type):
        _, exts, _ = ctx.get_type(e_type)
        for ext in exts:
            if filename.endswith(ext):
                return filename[:-len(ext)]
    return filename


# There's the <base> tag in HTML that allows you to set the base
# directory.  That would've been perfect for us, except... it only allows
# you to set one across the whole document.
#
# So yeah, we kind of have to do... this instead.
#
def replace_urls(doc, dirpath, relpath):
    """Append dirname to relative paths"""
    if not os.path.exists(dirpath):
        return doc
    soup = bs4.BeautifulSoup(doc, 'html.parser')
    for a_elem in soup.find_all('a'):
        # EAFP over LBYL
        try:
            href = a_elem['href']
        except KeyError:
            continue
        href = urllib.parse.unquote(href)
        if os.path.exists(os.path.join(dirpath, href)):
            a_elem['href'] = os.path.join(relpath, href)
    # only occasionally does the <video> tag contain source I guess?
    for src_elem in soup.find_all(['img', 'audio', 'source', 'video']):
        try:
            src = src_elem['src']
        except KeyError:
            continue
        src = urllib.parse.unquote(src)
        if os.path.exists(os.path.join(dirpath, src)):
            src_elem['src'] = os.path.join(relpath, src)
    # can't use soup.prettify() since it may add spurious space :(
    return str(soup)


def export_panels(panels, outdir, *, dumper=None, loader=None,
                  panel_formatter=None, encoding='utf-8', **kwargs):
    for invalid in {'sidebar_extra'}:
        if invalid in kwargs:
            raise ValueError(f'invalid keyword argument: {invalid!r}')
    if dumper is None:
        dumper = JSONDumper()
    if loader is None:
        loader = JSONLoader()
    loader.configure(error_on_warning=True)
    if panel_formatter is None:
        panel_formatter = PanelFormatter(infer_time_zone=False)
    panel_formatter.width = 120
    panel_formatter.configure(time_format=time_format)

    n_panels = len(panels)
    progress_bar = tqdm.tqdm(panels)
    updated = 0
    created = 0
    for index, panel in enumerate(progress_bar):
        dirpath = os.path.join(outdir, *str(panel.date).split('-'))
        bk_name = '.bk'
        bk = os.path.join(dirpath, bk_name)
        bk_json = os.path.join(bk, 'backup.json')
        bk_nav = os.path.join(bk, 'nav_info.json')
        nav_elements = []
        nav_info = {}
        if index > 0:
            prev_date = panels[index - 1].date
            prev_path = os.path.join(
                *['..'] * 3, *str(prev_date).split('-'), 'index.html')
            nav_elements.append(f'<a href="{prev_path}">Prev</a>')
            nav_info['prev'] = str(prev_date)
        if index < n_panels - 1:
            next_date = panels[index + 1].date
            next_path = os.path.join(
                *['..'] * 3, *str(next_date).split('-'), 'index.html')
            nav_elements.append(f'<a href="{next_path}">Next</a>')
            nav_info['next'] = str(next_date)
        nav_info['time_format'] = time_format
        nav_info['css'] = kwargs.get('css', None) or 'stylesheet.css'
        nav_info['mathjax'] = kwargs.get('mathjax', None) or MATHJAX_URL
        if os.path.exists(dirpath):
            loader.configure(base_dir=bk)
            try:
                with open(bk_json, encoding=encoding) as fp:
                    orig_panel = next(loader.load(fp))
                with open(bk_nav, encoding=encoding) as fp:
                    orig_nav_info = json.load(fp)
            except Exception:
                # whatever the heck happened it's a malformed backup
                # and we need to re-export them
                pass
            else:
                if orig_panel == panel and orig_nav_info == nav_info:
                    progress_bar.set_description(f'skipping {panel.date}')
                    continue
            action = 'updating'
            updated += 1
            shutil.rmtree(dirpath)
        else:
            action = 'creating'
            created += 1
        progress_bar.set_description(f'{action} {panel.date}')
        os.makedirs(bk)
        nav_elements.append('<a href="main.txt">Plain</a>')
        nav_elements.append(f'<a href="{bk_name}/backup.json">JSON</a>')
        content = '&nbsp;&nbsp;'.join(nav_elements)
        extra = f'<div class="card">{content}</div>'
        write_panel_html(panel, dirpath, sidebar_extra=extra, **kwargs)
        dumper.configure(base_dir=bk)
        with open(bk_json, 'w', encoding=encoding) as fp:
            dumper.dump([panel], fp)
        with open(bk_nav, 'w', encoding=encoding) as fp:
            json.dump(nav_info, fp)
        try:
            loader.configure(base_dir=bk)
            with open(bk_json, encoding=encoding) as fp:
                panel = next(loader.load(fp))
        except Exception:
            import sys, traceback
            print('RELOADING FAILED! removing it...', file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            shutil.rmtree(bk)
        panel_formatter.configure(base_dir=bk)
        with open(os.path.join(dirpath, 'main.txt'), 'w',
                  encoding=encoding) as fp:
            fp.write(panel_formatter.format(panel))
            fp.write('\n')

    parts = []
    if updated:
        s = '' if updated == 1 else 's'
        parts.append(f'updated {updated} panel{s}')
    if created:
        s = '' if created == 1 else 's'
        parts.append(f'created {created} panel{s}')
    if parts:
        print(' and '.join(parts).capitalize(), end='')
        print('.')
    else:
        print('No changes.')
