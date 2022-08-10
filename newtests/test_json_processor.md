`test_json_processor.py` in plain English because I am dumb ;-;

JSONLoader tests
================

TEST 1: date
------------

Test the `date` key at panel level.

1.  When not provided, ERROR ("panel must provide date")
2.  Must be a *str*
3.  Valid to `self.parse_date()`


TEST 2: time
------------

Test the `time` and `date-time` keys at entry level.
The optional `date` key when `time` is provided too.

1.  When neither is provided, ERROR ("entry must provide time")
2.  When both are provided (`time` and/or `date` when `date-time` is
    provided), ERROR ("exactly one ... can be provided")
3.  When `date` is provided, change the date of time LOCALLY
4.  When `date-time` is provided, ignore panel's date entirely
5.  When `date-time` and `date` are provided, `date` is ignored
6.  All attributes must be a *str*
7.  `time` is valid to `self.parse_time()`,
    `date-time` is valid to `self.parse_datetime()`,
    and `date` is valid to `self.parse_date()`.


TEST 3: data and input
----------------------

Test the `data` and `input` keys at entry level and the most
basic cases for inference.

1.  When neither is provided, ERROR ("at least one should be specified")
2.  When both are provided, ERROR ("only one ... can be specified")
3.  (inline text) When `data` is provided without `data-encoding`,
    enc = utf-8, type = plain (don't test inference yet, just test
    either all provided or nothing provided. no need to test get_data())
4.  (external file) When `input` is provided,
    enc = binary, type = binary (don't test inference yet)
5.  (inline binary) When `data` is provided with `data-encoding`,
    enc = binary, type = binary (again, don't test inference, but do
    test all data encodings)


TEST 4: rating
--------------

Test the `rating` key at panel level.

1.  When provided, used as the `rating` attribute.
2.  When not provided, `panel.has_rating()` should return False.
3.  Must be a `str`.


TEST 5: insight
---------------

Test the `insight` key at entry level.

1.  When provided, used as the `insight` property.
    When not provided, defaults to False.
2.  Must be a `bool`.


TEST 6: question
----------------

Test the `question` key at entry level.

1.  When provided, used as the `question` attribute.
2.  When not provided, `entry.has_question()` should return False.
3.  Must be a `str`.


TEST 7: time zone
-----------------

1.  Parsed by `self.parse_timezone()`.
2.  When provided as a TL attribute, used as default for all panels/entry.
3.  When provided as a panel-level attribute, used locally in a panel.
4.  When provided as an entry-level attribute, used exclusively to an entry.
5.  Any `tz` attribute completely when `date-time`/`time` string contains
    time zone info.
6.  If neither the `tz` attribute is set nor does `date-time`/`time` contain
    time zone info, ERROR ("time zone is not provided")

TODO: test fold attribute?


    (8) lookup paths
    (9) inference rules
    (10) panel & entry extensions


JSONDumper tests
================

TEST 1: top-level attributes
----------------------------

Test the interaction between `get_top_level_attributes()` and
the `time_zone` and `paths` options.  These are the top-level (TL)
attributes.

1.  The TL attribute `tz` is the option time_zone precisely
2.  The TL attribute `paths` is the option paths precisely


TEST 2: backup preparation
--------------------------

Test prepare_backup() given the top-level attributes.
These are the JSON top-level (JTL) attributes.

1.  The JTL attribute `tz` is the str returned by calling
    `self.format_timezone()` on the `tz` TL attribute if it
    is not None, otherwise unset
2.  The JTL attribute `paths` is the `paths` TL attribute
    if it is not equal to `['.']`, otherwise unset


InferenceManager tests
======================

    (1) alias_check
    (2) (enc2type) infer_type_from_encoding
    (3) (type2enc) infer_encoding_from_type
    (4) (path2type) infer_type_from_path


Function tests
==============

`find_paths()`

`get_lookup_paths()`
