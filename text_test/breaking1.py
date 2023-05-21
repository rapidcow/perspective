from json import dumps
from psp.serializers import text
from psp.ext.captions import CaptionTextLoader
from test1 import richify_logger

if __name__ == '__main__':
    richify_logger()
    text._DEBUG = 69
    print(dumps(CaptionTextLoader().loads(
"""\
# A comment
# Another comment
YEAR 2020
PATH ["../img"]
----------
DATE May 20
TIME 04:05 PM
INPUT ps-discussion.jpg
CAPTION Intelligent response involving the use of perfectly grammatical words
ATTR { "meta": { "created": "2020-02-21 16:05:09" } }
""")))
