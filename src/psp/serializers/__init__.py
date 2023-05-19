"""Serialization functions (formerly processors) for backup files."""

__all__ = []

# XXX: remove the json import too; this feels weird
from . import json
from .json import *
__all__.extend(json.__all__)
