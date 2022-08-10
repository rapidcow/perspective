.. _ext_captions:

==============================================================
:mod:`extensions.captions` --- Entries with captions and stuff
==============================================================

.. module:: psp.extensions.captions
   :synopsis: Entries with captions and stuff

I don't know about you, but whenever I see *this* with stringify it always
throws me off:

.. code-block:: text

                  Friday, September 7, 2018  :)


   2:18 AM
     <jpeg file sized 132.7 kB at 'BRANCHES/2018_G8S1/img/img_d
      ownload/2018-09-07_02-18-00_1.jpg'>

It says nothing about what the file contains!  If only there was a way to add
alt text or something so that at least I know what it says...

Well that's what this module does precisely.  With this extension added,
you can write

.. code-block:: json

   {
     "time": "02:18",
     "caption": "An octupus with comically large eyes... and a small jelly boi =D",
     "input": "2018-09-07_02-18-00_1.jpg"
   }

in your backup file, which will produce this!

.. code-block:: text

                  Friday, September 7, 2018  :)


   2:18 AM
     <jpeg file sized 132.7 kB at 'BRANCHES/2018_G8S1/img/img_d
      ownload/2018-09-07_02-18-00_1.jpg'>

     Caption: An octupus with comically large eyes... and a
              small jelly boi =D

This module defines three attributes at panel level: *caption* (as I've just
shown), *transcription*, and *title*.  Transcription may be used for a plain
text representation of binary files like images and audios.  And as for titles,
well, sometimes I like to title my entries, sort of like vignettes and blog
posts so... that's why.

.. describe the default state of all these three variables
