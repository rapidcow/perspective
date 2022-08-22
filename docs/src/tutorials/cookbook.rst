.. _pspcb:

====================
Perspective Cookbook
====================

The Perspective library is built with the ability to extend in mind, but
a good question to ask is *how*?  To answer that, here are some examples that
you might find useful.


.. _pspcb_0:

stringify doesn't look like the app interface in Perspective!!!
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Okay, okay.  Whether you came from :ref:`basicproc` or just decided to...
read, I guess.  I'm sorry I hadn't noticed this earlier okay?  But good
news: you can fix this very easily by subclassing
:class:`PanelFormatter <psp.stringify.PanelFormatter>`! ::

   class MyWayBetterPanelFormatter(PanelFormatter):
       def get_date_string(self, date):
           return date.strftime('%A, %b {date.day}, %Y')

   # To use this...
   formatter = MyWayBetterPanelFormatter()
   print(formatter.format(panel))

(notice the ``%b`` instead of ``%B``)


File types inference
^^^^^^^^^^^^^^^^^^^^

You may have noticed that (plain and binary are always inferred)

They are controlled by the context in ``filetypes``

There is currently no way to restrict a loader/dumper to a specific context
so if you want to do that you'll have to wrap your code in
``local_context()`` every time.


Swiching to json5
^^^^^^^^^^^^^^^^^

In case you want comments...


More date, time, and timezone!
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Out of the box JSONLoader only supports ISO format and fixed timezone offset

But you can change that!


Main program: speed
-------------------

quick check ::

    def load_singles(path, encoding, date):
        self.json_loader.configure(base_dir=os.path.dirname(path))
        with open(path, encoding=encoding) as fp:
            data = self.json_loader.load_json(fp)
        panels, attrs = self.json_loader.split_data(data)
        for panel in panels:
            panel_date = self.json_loader.parse_date(panel['date'])
            if panel_date == date:
                yield self.json_loader.process_panel(panel, attrs)
