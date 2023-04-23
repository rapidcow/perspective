from json import dumps
from psp.serializers import text
from test1 import richify_logger

if __name__ == '__main__':
    richify_logger()
    text._DEBUG = 69
    print(dumps(text.TextLoader().loads("""
DATE Apr 21 2023
TIME 22:40
<<<<<
content began with five <'s, so we'd expect five >'s
not this:
>>>
or any this:
>>>>>>>>
>>>>> i like trains
but precisely, this:
>>>>>
    """), indent=2))
    print(dumps(text.TextLoader().loads("""
      DATE APRIL 1 2023
      # panel attributes
      RATING :D
      ATTR {
        "custom-attribute": "foo!"
      }

      TIME 12:30
      # entry attributes
      TYPE markdown
      FORMAT pandoc
      QUESTION How was your day?
      ATTR {
        "custom-attribute": "bar!"
      }
    """), indent=2))
