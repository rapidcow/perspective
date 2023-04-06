"""Helpers for serialization"""
__all__ = ['InferenceManager']

import collections
import os
from .. import filetypes


class InferenceManager:
    """Manager of the inference rules."""
    __slots__ = ()

    def alias_check(self, name):
        """Return the name of a file type if `type` is an alias of
        it, else return `type`.
        """
        return filetypes.get_context().alias_check(name)

    def infer_type_from_encoding(self, enc):
        """Infer file type from encoding.  enc is None if user didn't
        provide a value, otherwise it is a str.  This method should
        return a str or None upon failure.
        """
        if enc is None:
            return None
        return 'binary' if enc == 'binary' else 'plain'

    def infer_encoding_from_type(self, type):
        """Infer encoding from file type.  type is a str.
        This method should return a str or None upon failure.  The str
        should be precisely 'binary' for a binary file and any other
        str for a text file.
        """
        ctx = filetypes.get_context()
        try:
            is_text = ctx.is_text_type(type)
        except LookupError:
            return None
        return 'utf-8' if is_text else 'binary'

    def infer_type_from_path(self, filepath):
        """Infer file type from file path.  filepath is a str.
        This method should return a str when inference is successful
        or return None upon failure.
        """
        ctx = filetypes.get_context()
        parts = os.path.basename(filepath).split('.')
        # The part after a leading dot is not an extension
        if parts and not parts[0]:
            del parts[0]
        # Strip out the file name part.  The rest are all going to be
        # tested for extension.
        extparts = collections.deque(f'.{part}' for part in parts[1:])
        # Prefer the longest possible extension to shorter ones
        while extparts:
            try:
                return ctx.extension_to_type(''.join(extparts))
            except LookupError:
                extparts.popleft()
        return None
