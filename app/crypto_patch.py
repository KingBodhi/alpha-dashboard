import hashlib

def ripemd160_sha256(data):
    sha = hashlib.sha256(data).digest()
    try:
        # Try system hashlib first
        return hashlib.new('ripemd160', sha).digest()
    except (ValueError, TypeError):
        # Fallback to PyCryptodome
        try:
            from Crypto.Hash import RIPEMD160
        except ImportError as e:
            raise RuntimeError(
                "Your system lacks ripemd160 and pycryptodome is not installed. "
                "Install it with 'pip install pycryptodome'."
            ) from e

        h = RIPEMD160.new()
        h.update(sha)
        return h.digest()
