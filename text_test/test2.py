from json import dumps
from psp.serializers import text
from test1 import richify_logger

if __name__ == '__main__':
    richify_logger()
    text._DEBUG = 69
    with open('2.txt', encoding='utf-8') as fp:
        print(dumps(text.TextLoader().load(fp), indent=2))
    print(dumps(text.TextLoader().loads("""
   daTe 'march'  03\ \ 2023
   TimE   12":"30
   <
   hi
   >
    """), indent=2))
