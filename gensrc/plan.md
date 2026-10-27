# genpsp plan

Working notes; nothing here is final.

## Goals

- A general model for diaries and imported notes (trivnote is the
  other consumer): a tree of nodes with open attributes.
- Keep `psp.types` (`Panel`, `Entry`) source-compatible as specializations
  of that tree.
- Replace MRO-based extensions with a registry.
- An S-expression file syntax that Python (here) and Java (libexpr)
  can both read.

## Non-goals

- Optimizing storage or performance; trivnote is an import tool.
- Assuming ids are UUIDs.  The general model treats ids as opaque strings.
- CRLF.  Files are LF only.
- A GUI.  CLI first.

## Data model

    Node(id: str | None, kind: str, attrs: dict, children: list, parent)

- One parent per node.  Child order is file order.
- `Panel(Node)`: kind `panel`; `date` is a required key.  A topical
  container for one day.
- `Entry(Node)`: kind `entry`; `time` is a required key; entries are
  chronological within a panel.  Entries may have child entries
  (e.g. replies in the weixin archive).
- Arbitrary attributes, e.g. `(insight . #t)`, `(question . "...")`,
  `(rating . ":)")`.  Unknown attributes round-trip untouched.
- Folders are nodes too (kind `folder`), so a tree like Apple Notes'
  falls out; folder attributes (rating, default type, tz) are ordinary
  attributes.
- Dates versus folders are two axes: the folder tree is
  user-chosen; calendar views come from a derived index.

### Attribute registry

Replaces `Configurable`, `MetaEntry._metavars` and `extname` class-level
MRO walks:

    Attr(key, kinds, parse, dump, inherit=False, default=None)

- An extension is a list of `Attr`s plus optional handlers for entry
  `type`s.  Loaders, dumpers and formatters iterate the registry; they
  are not subclassed per extension.
- Registering a duplicate key is an error.
- Lookup: nearest ancestor that sets the key, if `inherit` is true
  (`tz` already works this way).  Lists replace; no merging.

### Identity

- Ids are opaque strings in the general model.
- Panels: deterministic natural key, `psp:panel:YYYY-MM-DD`.  Two devices
  that create the same day agree; entries union on merge.
- Entries: random, generated at creation, **persisted** in the file as
  `(id . "...")`.  Entries are not identifiable by date and time, and
  they are edited and moved over time, so the id must survive both.
- psp scheme: 12 random Crockford base32 characters (60 bits), shown as
  `k3f9-x2mq-7ztd`.  Not time-ordered, so nobody reads meaning into it.
  Uniqueness is checked against the archive at creation.
- Identity is not revision.  `created`/`posted`/`modified` metadata
  serves as revision info; no history mechanism until needed.
- Duplicate ids in one archive are a load error (a copy-pasted block);
  `psp ids --fix` re-ids the later one.
- `Entry.copy()` gets a fresh identity; `from_entry()` (re-wrapping)
  preserves the id.

## File syntax

Node = `(kind alist . children)`, i.e. SXML-like:

    (panel ((date . "2020-08-23") (rating . ":)"))
      (entry ((id . "k3f9-x2mq-7ztd") (time . "01:44")
              (type . "markdown") (insight . #t)
              (data . #<<EOF
    text, verbatim
    EOF
    ))))

- Heredoc: Racket's `#<<TAG`, no indentation stripping (keeps the grammar
  small).  May be extended later.
- Comments: `;` and `#;`.
- The python reader takes the JSON-equivalent subset only; richer
  datums stay in libexpr.
- LF only.
- A `SexpLoader` adapter turns nodes into the dict `JSONLoader.load_data`
  already takes, so the existing loaders keep working.

## Compatibility with `psp.types`

- `Panel` and `Entry` become single-inheritance subclasses of `Node`.
  `entries()`, `add_entry`, `get_rating`, `get_attribute(s)`, `sort_entries`,
  `time`, `panel`, `insight` stay as thin methods over `children`/`attrs`.
- `insight` becomes an attribute; the property stays and still validates
  against the parent.
- The old mixin path (`make_panel_class`, `extname`) keeps working during
  the transition and is removed once nothing depends on it.
- Real usage to keep working: `~/archive/journals/diary/perspective/{lib,scripts}`
  and the weixin archive (`posts.py`: `Post` and `Reply` move to child
  entries; `poster`, `media` become attributes).

## Migration

- `psp ids --write` assigns ids to existing entries and writes them back.
- Until then the loader derives a deterministic placeholder (hash of panel
  date, time and position).  Never treated as permanent identity.

## Milestones

1. `Node`, `Attr` registry, ids; tests.
2. `Panel`/`Entry` rebased onto `Node`; `newtests/test_types.py` passes
   unchanged.
3. S-expression syntax spec and the Python reader/writer.
4. `SexpLoader`/`SexpDumper` on top of `JSONLoader`/`JSONDumper`.
5. Port the caption/meta/big extensions to the registry.
6. Re-fit weixin `Post`/`Reply` as a test of the model.
7. CLI: capture, query/index, HTML export.

## Open questions

- Representation of `null`: a token, or an omitted key?
- Do folders live on disk as directories, or only in the file syntax?
- Shape of the derived index (SQLite?) and what it covers.
- Whether Java (libexpr) needs a node-aware layer or just reads datums.
