"""Export panels to HTML.  Something I wrote personally to compensate
for the lack of images from the terminal output...

This script relies on three external packages you should probably install
using pip in advance:

* pandoc (used to parse Markdown entries)
* pyheif (for reading HEIC files if you use iOS like me... >_>)
* tqdm (fancy progress bar)

And of course, you should install my psp package too. ;)
"""

import datetime
import html
import json
import os
import re
import shutil
import subprocess
import tempfile

import pandoc
import pandoc.types
import psp.util
import psp.datatypes
import psp.timeutil
from psp.stringify import PanelFormatter, EntryFormatter
from psp.extensions.bigentry import BigEntry, BigLoader, BigDumper
import tqdm

__all__ = ['write_panel_html', 'export_panels']

time_format = '24 hour'

TEMPLATE = """<!DOCTYPE html>
<html lang="en-US">
<head>
  <meta charset="utf-8">
  <title>{TITLE}</title>
  <link rel="stylesheet" href="stylesheet.css" />
  <script type="text/javascript" id="MathJax-script" async
    src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js">
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

img {
  padding: 0 3ex 0 3ex;
  width: 80%;
  /* Centering */
  display: block;
  margin: 0 auto;
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

def by_utc(entry):
    return psp.timeutil.to_utc(entry.date_time)


def write_panel_html(panel, dirpath, filename='main.html',
                     sidebar_extra=''):
    """Export a panel to an HTML file inside the directory 'dirpath'."""
    panel_title = panel.date.strftime('%A, %B %e, %Y')
    rating = panel.get_attribute('rating', None)
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
    main_entries.sort(key=by_utc)
    insight_entries.sort(key=by_utc)

    entries_html_parts = []
    dircount = 0
    dircount = add_entries(entries_html_parts, main_entries, dirpath,
                           dircount, '<div class="card">', '</div>')
    if insight_entries:
        entries_html_parts.append(INSIGHT_CARD)
    dircount = add_entries(entries_html_parts, insight_entries, dirpath,
                           dircount, '<div class="insight card">', '</div>')
    no_entries_card = '<div class="card"><p>no entries...</p></div>'
    entries_html = ''.join(entries_html_parts).rstrip('\n') or no_entries_card

    sidebar = get_status_html(panel) + sidebar_extra
    text = TEMPLATE.format(TITLE=panel_title, HEADER=title_html,
                           LEFT=entries_html, RIGHT=sidebar)
    with open(os.path.join(dirpath, filename), 'x') as fp:
        fp.write(text)
    with open(os.path.join(dirpath, 'stylesheet.css'), 'x') as fp:
        fp.write(STYLESHEET)


def add_entries(parts, entries, parent_dir, dircount, lefttag, righttag):
    relpath = str(dircount)
    dirpath = os.path.join(parent_dir, relpath)
    for entry in entries:
        parts.append(lefttag)
        parts.append('\n')
        parts.append(get_entry_html(entry, dirpath, relpath))
        parts.append(righttag)
        parts.append('\n')
        # Only advance directory count if we exported something
        if os.path.exists(dirpath):
            dircount += 1
            relpath = str(dircount)
            dirpath = os.path.join(parent_dir, relpath)
    return dircount


def get_entry_html(entry, dirpath, relpath):
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
        if file_type == 'markdown':
            content = markdown_to_html(entry, dirpath, relpath)
        elif file_type == 'tex':
            content = tex_to_html(entry, dirpath, relpath)
        elif file_type == 'plain':
            content = plain_to_html(entry)
        else:
            raise ValueError(f'unsupported bigentry file type: '
                             f'{file_type!r}')
        return content
    if entry.is_text():
        if entry_type == 'markdown':
            return markdown_to_html(entry, dirpath, relpath)
        # Fallback
        parts = []
        entry_head(parts, entry)
        parts.append('<pre class="no-bg">')
        parts.append(html.escape(get_entry_text(entry)))
        parts.append('</pre>\n')
        return ''.join(parts)
    if entry_type in {'png', 'jpeg', 'heic'}:
        os.mkdir(dirpath)
        ext = psp.datatypes.get_extension(entry_type)
        basename = 'image'
        if entry_type == 'heic':
            ext = '.jpg'
            import pyheif
            from PIL import Image
            filepath = os.path.join(dirpath, basename + ext)
            heif_file = pyheif.read(entry.get_data())
            im = Image.frombytes(
                heif_file.mode,
                heif_file.size,
                heif_file.data,
                'raw',
                heif_file.mode,
                heif_file.stride)
            im.save(filepath, format='jpeg')
        else:
            filepath = os.path.join(dirpath, basename + ext)
            entry.export(filepath)
        parts = []
        entry_head(parts, entry)
        parts.append('<img')
        caption = entry.get_attribute('caption', '')
        if caption:
            parts.append(f' alt="{html.escape(caption)}"')
        parts.append(f' src="'
                     f'{html.escape(os.path.join(relpath, basename + ext))}"')
        parts.append(' />\n')
        return ''.join(parts)
    # Default scenario for a file
    parts = []
    entry_head(parts, entry)
    ext = psp.datatypes.get_extension(entry_type, default='')
    basename = 'something'
    filepath = os.path.join(dirpath, basename + ext)
    os.mkdir(dirpath)
    entry.export(filepath)
    parts.append(f'<a href="'
                 f'{html.escape(os.path.join(relpath, basename + ext))}">'
                 f'<pre class="no-bg">'
                 f'{html.escape(basename + ext, quote=False)}'
                 f'</pre></a>\n')
    return ''.join(parts)


def get_status_html(panel):
    """Get the status of the panel 'panel' as an HTML div element."""
    entry_count = sum(1 for e in panel.entries())
    stuff = (f'<p>Entries: {entry_count}</p>\n'
             f'<p>I don\'t know what else to put here</p>\n')
    return '<div class="card">\n' + stuff + '</div>'


# The real work
def entry_head(parts, entry):
    global time_format
    title = (EntryFormatter(time_format=time_format)
             .get_title(entry.panel.date, entry.date_time))
    parts.append('<h2>')
    parts.append(html.escape(title).replace(' ', '&nbsp;'))
    parts.append('</h2>\n')
    attrs = []

    question = entry.get_attribute('question', '')
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

    desc = entry.get_meta_attribute('desc', '')
    if desc:
        attrs.append(('Description', desc))

    created = entry.get_meta_attribute('created', None)
    if created is not None:
        attrs.append(('Created', str(created)))

    modified = entry.get_meta_attribute('modified', None)
    if modified is not None:
        attrs.append(('Modified', str(modified)))

    posted = entry.get_meta_attribute('posted', None)
    if posted is not None and posted != entry.date_time:
        attrs.append(('Posted', str(posted)))

    caption = entry.get_attribute('caption', '')
    if caption:
        attrs.append(('Caption', caption))

    tr = entry.get_attribute('transcription', '')
    if tr:
        attrs.append(('Transcription', tr))

    for term, value in attrs:
        parts.append('<div class="card-attr">\n')
        # Only un-hide the HTML comments i guess
        value = value.replace('<!--', '&lt;!--').replace('-->', '--&gt;')
        # parts.append('  <pre class="no-bg">')
        # parts.append(term + ': ')
        # parts.append(html.escape(value))
        # parts.append('</pre>\n')
        parts.append(replace_stuff_for_monospace(
            pandoc.write(pandoc.read(f'{term}: {value}'), format='html',
                         options=['--mathjax'])))
        parts.append('</div>\n')


def get_entry_text(entry):
    return replace_stuff_for_monospace(entry.get_data())


def replace_stuff_for_monospace(text):
    return text.replace('…', '...').replace('–', '--').replace('—', '---')


def plain_to_html(entry):
    parts = []
    entry_head(parts, entry)
    parts.append('<pre class="no-bg">\n')
    parts.append(html.escape(get_entry_text(entry)))
    parts.append('</pre>')
    return ''.join(parts)


def markdown_to_html(entry, dirpath, relpath):
    parts = []
    entry_head(parts, entry)
    pandoc_format = entry.get_meta_attribute('pandoc-format', 'markdown')
    doc = pandoc.read(get_entry_text(entry), format=pandoc_format)
    for element in pandoc.iter(doc):
        if isinstance(element, pandoc.types.Image):
            img_path, fig_str = element[2]
            if not img_path.startswith('https'):
                element[2] = (os.path.join(relpath, img_path), fig_str)
    if isinstance(entry, BigEntry):
        entry.extractall(dirpath)
        os.unlink(os.path.join(dirpath, entry.get_main_file()))
    parts.append(replace_stuff_for_monospace(
        pandoc.write(doc, format='html', options=['--mathjax'])))
    return ''.join(parts)


# ONLY bigentry should call this
def tex_to_html(entry, dirpath, relpath):
    parts = []
    entry_head(parts, entry)
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
    with tempfile.TemporaryDirectory() as tmpdir:
        if isinstance(entry, BigEntry):
            entry.extractall(tmpdir)
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
                retval = subprocess.call([
                    engine, '-shell-escape', '-output-directory',
                    outdir, filename])
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
        entry.extractall(dirpath)
        os.unlink(os.path.join(dirpath, entry.get_main_file()))
    return ''.join(parts)


def export_panels(panels, outdir, *, dumper=None, loader=None,
                  panel_formatter=None, entry_formatter=None):
    if dumper is None:
        dumper = BigDumper(
            default_time_zone_offset=datetime.timedelta(hours=8))
    if loader is None:
        loader = BigLoader(error_on_warning=True)
    if panel_formatter is None:
        panel_formatter = PanelFormatter()
    panel_formatter.width = 120
    panel_formatter.configure(time_format=time_format)
    if entry_formatter is None:
        entry_formatter = EntryFormatter()

    n_panels = len(panels)
    progress_bar = tqdm.tqdm(panels)
    for index, panel in enumerate(progress_bar):
        dirpath = os.path.join(outdir, *str(panel.date).split('-'))
        bk = os.path.join(dirpath, '_bk')
        nav_elements = []
        nav_info = {}
        if index > 0:
            prev_date = panels[index - 1].date
            prev_path = os.path.join(
                *['..'] * 3, *str(prev_date).split('-'), 'main.html')
            nav_elements.append(f'<a href="{prev_path}">Prev</a>')
            nav_info['prev'] = str(prev_date)
        if index < n_panels - 1:
            next_date = panels[index + 1].date
            next_path = os.path.join(
                *['..'] * 3, *str(next_date).split('-'), 'main.html')
            nav_elements.append(f'<a href="{next_path}">Next</a>')
            nav_info['next'] = str(next_date)
        if os.path.exists(dirpath):
            loader.configure(base_dir=os.path.join(dirpath, '_bk'))
            try:
                orig_panel = loader.load(os.path.join(bk, 'backup.json'))[0]
                with open(os.path.join(bk, 'nav_info.json')) as fp:
                    orig_nav_info = json.load(fp)
            except FileNotFoundError:
                pass
            else:
                if (psp.util.panels_equal(orig_panel, panel)
                        and orig_nav_info == nav_info):
                    progress_bar.set_description(f'skipping {panel.date}')
                    continue
            action = 'updating'
            shutil.rmtree(dirpath)
        else:
            action = 'creating'
        progress_bar.set_description(f'{action} {panel.date}')
        os.makedirs(dirpath)
        nav_elements.append('<a href="main.txt">Plain</a>')
        if nav_elements:
            content = '&nbsp;&nbsp;'.join(nav_elements)
            extra = f'<div class="card">{content}</div>'
        else:
            extra = ''
        write_panel_html(panel, dirpath, sidebar_extra=extra)
        dumper.dump([panel], bk)
        with open(os.path.join(bk, 'nav_info.json'), 'w') as fp:
            json.dump(nav_info, fp)
        loader.configure(base_dir=bk)
        panel_formatter.configure(base_dir=bk)
        panel = loader.load(os.path.join(bk, 'backup.json'))[0]
        with open(os.path.join(dirpath, 'main.txt'), 'w') as fp:
            fp.write(panel_formatter.format(
                panel, entry_formatter=entry_formatter))
            fp.write('\n')