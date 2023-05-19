from json import dumps
from psp.serializers import text
from psp.ext.bigentry import BigTextLoader
from psp.ext.captions import CaptionTextLoader
from test1 import richify_logger

if __name__ == '__main__':
    richify_logger()
    text._DEBUG = 69
    print(dumps(BigTextLoader().loads("""
TIME ZONE Asia/Hong_Kong
YEAR 2023  # L + ratio
ATTR { "ratio": [5, 19] }
DATE Apr 21
TIME 22:40
INPUT some-path.zip
MAIN-FILE some
    """), indent=2))
    print(dumps(CaptionTextLoader().loads("""
DATE Apr 21 2023
TIME 22:40
INPUT some-path.jpg
TYPE jpg
CAPTION <<<
A kind of secret image
>>>
    """), indent=2))
