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

        def load_json(self, file, encoding):
            with open(file, encoding=encoding) as fp:
                return json.load(fp)

        def load_all(self, data):
            return super().load_data(data)

        def load_single(self, data, date):
            return super().load_data(data, date=date)


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
            self.formatter.configure(base_dir=os.getcwd())

        def print(self, panel, file):
            print(self.formatter.format(panel), file=file)


    # The 'calendar' command would use this
    firstweekday = calendar.MONDAY
