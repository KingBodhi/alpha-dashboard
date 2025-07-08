import hashlib
from functools import partial

# Save the original constructor
original_new = hashlib.new

def patched_new(name, data=b'', **kwargs):
    if name.lower() == 'ripemd160':
        try:
            # Try system
            return original_new(name, data, **kwargs)
        except (ValueError, TypeError):
            # Fallback to PyCryptodome
            try:
                from Crypto.Hash import RIPEMD160
            except ImportError:
                raise RuntimeError(
                    "Your system lacks ripemd160 and pycryptodome is not installed. "
                    "Install with: pip install pycryptodome"
                )
            h = RIPEMD160.new()
            h.update(data)
            return h
    return original_new(name, data, **kwargs)

# Patch it globally
hashlib.new = patched_new
