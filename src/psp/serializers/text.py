"""Plain text processors"""
from ..types import Configurable

__all__ = ['TextLoader', 'TextDumper', 'load_text', 'dump_text']


# XXX More useful docstring
class TextLoader(Configurable):
    """Text loader"""
    __slots__ = ()


class TextDumper(Configurable):
    """Text dumper"""
    __slots__ = ()


def load_text():
    pass


def dump_text():
    pass
