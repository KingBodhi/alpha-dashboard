#!/usr/bin/env python3
"""
Test script to check what address types the bit library actually generates.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Apply the same hashlib patch as in profile_page.py
import hashlib

_original_hashlib_new = hashlib.new

def patched_hashlib_new(name, data=b'', **kwargs):
    if name.lower() == 'ripemd160':
        try:
            return _original_hashlib_new(name, data, **kwargs)
        except (ValueError, TypeError):
            try:
                from Crypto.Hash import RIPEMD160
            except ImportError as e:
                raise RuntimeError(
                    "Your system lacks ripemd160 in OpenSSL and pycryptodome is not installed.\n"
                    "Fix with:\n\n    pip install pycryptodome"
                ) from e
            h = RIPEMD160.new()
            h.update(data)
            return h
    return _original_hashlib_new(name, data, **kwargs)

hashlib.new = patched_hashlib_new

from bit import Key

def test_address_generation():
    """Test what address types the bit library generates."""
    print("Testing Bitcoin address generation with bit library...")
    print("=" * 60)
    
    # Generate a new key
    key = Key()
    
    print(f"Private Key (WIF): {key.to_wif()}")
    print(f"Public Key: {key.public_key.hex()}")
    print()
    
    # Check available address properties
    print("Available address types:")
    print(f"key.address (legacy): {key.address}")
    
    # Check if segwit_address exists and what it generates
    if hasattr(key, 'segwit_address'):
        print(f"key.segwit_address: {key.segwit_address}")
    else:
        print("key.segwit_address: NOT AVAILABLE")
    
    # Check other possible address properties
    for attr in dir(key):
        if 'address' in attr.lower() and not attr.startswith('_'):
            try:
                value = getattr(key, attr)
                if isinstance(value, str) and (value.startswith('1') or value.startswith('3') or value.startswith('bc1')):
                    print(f"key.{attr}: {value}")
            except:
                pass
    
    print()
    print("Address Type Analysis:")
    print(f"Legacy (P2PKH): {key.address} - Starts with '1'")
    
    if hasattr(key, 'segwit_address'):
        segwit = key.segwit_address
        if segwit.startswith('3'):
            print(f"P2SH-wrapped Segwit: {segwit} - Starts with '3'")
        elif segwit.startswith('bc1'):
            print(f"Native Segwit (bech32): {segwit} - Starts with 'bc1'")
        else:
            print(f"Unknown segwit format: {segwit}")
    
    print()
    print("CONCLUSION:")
    print("The 'bit' library does NOT generate native segwit (bech32, bc1...) addresses.")
    print("It only generates:")
    print("1. Legacy addresses (P2PKH, starting with '1')")
    print("2. P2SH-wrapped segwit addresses (starting with '3')")
    print()
    print("To generate native segwit addresses, we need a different approach.")

if __name__ == "__main__":
    test_address_generation()
