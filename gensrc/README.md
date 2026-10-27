# genpsp - general perspective

A small, general model for diaries and imported notes: a tree of
nodes with open attributes, plus an S-expression file syntax.  It
generalizes the data types of the `psp` library (panels and entries)
without breaking them.

Status: planning.  See [plan.md](plan.md).

Licensed under the GNU General Public License version 3 or later
(GPLv3+); see `LICENSE`.

## Development

    python3 -m pip install -e .
    python3 -m unittest discover tests
