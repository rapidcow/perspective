Panel test
==========

Test 1: Initialization
----------------------

1.  `date` is the one and only required positional-argument.
2.  `date` must be a `datetime.date` instance.
3.  The argument is stored under the read-only property `date`.


Test 2: `__repr__`
------------------

1.  `repr(self)` returns `<Panel on ...>` where `...` is the string
    representation of `self.date`.


Test 3: Entry list addition / removal
-------------------------------------

Test the `add_entry`, `remove_entry()`, and `has_entry()` methods of
`Panel` and the `panel` attribute and the `has_panel()` method of `Entry`.

1.  `add_entry()` appends an entry to the end of a panel's entry list,
    unless it is already added, in which case, ValueError.
2.  `remove_entry()` removes an entry if it is in panel (in terms of
    IDENTITY, not EQUALITY); ValueError otherwise.
    (And because how `add_entry()` shouldn't append an entry that is added
    beforehand, two successive calls to `remove_entry()` should never work.)
3.  If `add_entry()` is called with an entry already added to a different
    panel, `remove_entry()` of that panel is called to prior to adding.
4.  `self.has_entry(entry)` should be equivalent to `entry.panel is self`.
    (No need to fuss over the "always", just make sure to include minimal
    obvious exceptions)


Problems to look out for (can't call these issues since that should be
reserved for GitHub issues):

1.  Due to membership (the `in` operator) and `list.remove()` relying on
    equality checking rather than identity, we need to be extra careful
    that `remove_entry()` and `has_entry()` don't do the same thing.
    ([This](https://stackoverflow.com/a/58761459) explores a similar
    solution to what I wanted here.)

    Highlights of the tests added due to this:

    1.  (Test 3.1) If `e1 == e2`, but `e1 is not e2`, adding the two entries
        should not evoke any exceptions, and `panel.count() == 2`.
    2.  (Test 3.4) If `e1` is added but `e2` is not (where, again,
        `e1 == e2`), `has_entry(e2)` should return False (even though
        `e2 in get_entries()` is True).
    3.  (Test 3.2) Assuming the entries were added in the said order,
        `remove_entry(e2)` should preserve `e1`.  (If `remove_entry()`
        was implemented with `list.remove()`, `e1` would be removed.)


Test 4: Entry list operations
-----------------------------




Test 5: Equality
----------------

Test 6: `from_panel` and copying
--------------------------------

TODO: More!


Entry test
==========

Test 1: Initialization
----------------------

Test 2: `__repr__`
------------------

Test 3: Validation
------------------

also tests the cases where entry has a panel and where entry doesn't

Test 3: 

    (1) data attributes (type, encoding, format, raw, source)
    (2)

Test ?: Equality
----------------

Test ?+1: `from_panel` and copying
----------------------------------


Common Tests
============

*   attribute protocol
*   extensions
