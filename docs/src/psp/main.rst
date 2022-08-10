.. _main_program:

============================
:mod:`main` --- Main Program
============================

--config, -c     Configuration
--date, -d       Date

Default configuration::

    import calendar
    import json
    import os
    from psp.processors.json_processor import JSONLoader, JSONDumper
    from psp.stringify import PanelFormatter


    # This class is used to load backup files.
    # The load_json() method is first called to read from
    # a JSON file, then load_all() or load_single() is called
    # to extract either all panels or just one.
    class BackupLoader(JSONLoader):
        __slots__ = ()

        def configure(self, **kwargs):
            super().configure(**kwargs)

        def load_all(self, file, encoding):
            return super().load(file, encoding=encoding)

        def load_single(self, file, encoding, date):
            return super().load(file, date=date, encoding=encoding)


    # TODO: add explanation and stuff
    class BackupDumper(JSONDumper):
        __slots__ = ()

        def dump(self, panels, dirname, encoding):
            super().dump(panels, dirname, encoding=encoding)


    class Printer:
        # This is just one way to implemented it btw;
        # the 'formatter' attribute won't be accessed.
        __slots__ = ('formatter',)

        def __init__(self, width):
            self.formatter = PanelFormatter(width)
            self.formatter.configure(base_dir='.')

        def print(self, panel, file):
            print(self.formatter.format(panel), file=file)


    # The 'calendar' command would use this
    firstweekday = calendar.MONDAY

.. TODO base_dir doesn't have to be os.getcwd() ("." would do!)
        no need to import os either
