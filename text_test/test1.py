# this test requires the rich library: pip install rich
from json import dumps
import logging
from psp.serializers import text
from rich.logging import RichHandler
from rich.console import Console

def richify_logger():
    logger = logging.getLogger('psp.serializers.text')
    logger.setLevel(logging.DEBUG)
    ch = RichHandler(console=Console(stderr=True))
    ch.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(ch)

if __name__ == '__main__':
    richify_logger()
    text._DEBUG = 69
    loader = text.TextLoader()
    with open('1.txt', encoding='utf-8') as fp:
        print(dumps(loader.load(fp), indent=2))
