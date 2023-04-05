
- [ ] make backups optional when running update
- [ ] only update files that are changed in
    * rename old files to `*.old`
    * "delete" old files by moving it to a designated trash file
    * upon failure, print out files that were added
    * on success, unlink the `*.old` files and "deleted" files
- [ ] rename psp.main -> psp.cli, psp.main.tools -> psp.cli.util
      (i really don't have a better name for this)
- [ ] rename psp.processors -> psp.serializers, json_processor -> simply json
    * make it clear that users do not want to import directly from any of them; just using `from psp.serializers import ...` should be enough
    * also XXX: does JSONDumper check ambiguous directory names? what about big entries referring to directories??? (how does it make sense to serialize then????? maybe we should just still stick to archive files & find some other way for users to edit them.....)
    * add a new processor like [plainconv](https://gist.github.com/rapidcow/c2dda740d428db832b91b82e265a3b01) for simple text format (we can consider adopting YAML/HTML 5/etc)
- [ ] make `get_*_extensions` return a list of strings, and let `make_*_class` return something based on them (may prepare a lookup table for extension classes similar to `sys.modules` except for classes)

    RATIONALE: make it so that it is possible to inject entries into Django database (along with perhaps static files???)
- [ ] make it so that psp program searches for a special file like .git/ (.psp/? with the .psp/config.json stuff??)
    * points to scripts/config.py for configuration and scripts/main.py for entry point (ONLY for CLI use, put EVERYTHING else in config.py)
    * make a main function parser that allows custom callbacks to be added for subcommands!!!
    * also python -m psp should be equivalent to psp itself...
- [ ] more friendly prompting for creating a psp project
    * scripts location? (optional)
        - also put lib with the scripts, awkward import hacks are awkward
    * implement partitions? (optional, also include a brief description why partitions are recommended)
        - also also, add a checkpartitions subcommand for this case, which checks if partitions are mutually exclusive and actually contain panels within those ranges
    * journal title? (optional)
    * MORE TUTORIAL!!!!!
- [ ] i'm gonna fall asleep.........
- [ ] serialize, deserialize, with inherent attributes, extra attributes, and extension names
