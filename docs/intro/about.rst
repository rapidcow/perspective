.. _what is this?:

-------------
What is this?
-------------

The Perspective library is one of my personal coding projects which I
decided to upload to `a GitHub repository
<https://github.com/rapidcow/perspective>`_ due to how useful it has become
to me.  This right here is a little documentation for all the gibberish
source code and stuff I have.

As for basicproc.py_, well, you can say it was a prototype of the library.
It had all the core concepts like time zone, lookup paths, and the keys,
except too many functionalities are condensed into one single class.
Over time it grew larger (> 1000 lines) and adding new features like
exporting entries and formatting different time zones was impossible without
terrible exploitation of the syntax, so the Perspective library was made to
replace it and extend the features from there on.

.. _basicproc.py: https://gist.github.com/rapidcow/a0490a57965061ae06e5c43b2c97e46c

I chose to include it not because of its practical uses but the ideas I've
established while designing it, which more or less are copied directly into
the Perspective library.  But to be honest, I think I'll have to sort out
these things before I can call it final... (haha if only I had time to XD)

There are two objectives I would like to achieve with this library:

*  A tool to help back up entries from the iOS journaling app Perspective
   (and diaries in general!)
*  A programming interface for doing fancy stuff to the backup files

.. TODO Make some fun examples
