`test_bigentry.py`

Managers
========

extract_all must be safe!!!


BigEntry tests
==============

* TEST 1: NEW accessors and setters (main file, mf type, mf format,
          mf encoding)
* TEST 2: type = a binary type, encoding = binary, format is disabled

everything that has to do with the BigEntryManager, INCLUDING:

* TEST 3: manager interface (add, remove, list all, also inheritance hook)
* TEST 4: text-related functions (is_text, get_data, stream_data)
* TEST 5: extract all


BigLoader tests
===============

* TEST 1: Big entry information
* TEST 2: Input path lookup
* TEST 3: Raw data decoding


BigDumper tests
===============

* TEST 1: Big entry information
* TEST 2: Exporting
* TEST 3: Raw data encoding

TEST 2:

1.  If big entry, export to doc
2.  Otherwise, leave default directory
