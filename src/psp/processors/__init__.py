"""i have no idea why i turned this into a package
please don't kill me
"""

__all__ = []

from . import json_processor
from .json_processor import (JSONLoader, JSONDumper, load_json,
                             load_json_with_filter, dump_json)
__all__.extend(['JSONLoader', 'JSONDumper', 'load_json',
                'load_json_with_filter', 'dump_json'])
