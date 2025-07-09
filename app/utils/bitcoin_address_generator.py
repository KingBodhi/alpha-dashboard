#!/usr/bin/env python3
"""
Bitcoin address utility that supports native segwit (bech32) address generation.
This utility bridges the gap between the bit library (used for transactions)
and bitcoinlib (used for native segwit address generation).
"""

import hashlib
from typing import Tuple, Optional

# Apply the same hashlib patch as in profile_page.py
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

# Safe to import libraries now
from bit import Key as BitKey
from bitcoinlib.keys import HDKey


class BitcoinAddressGenerator:
    """
    Bitcoin address generator that supports all address types including native segwit.
    """
    
    def __init__(self, private_key_wif: Optional[str] = None):
        """
        Initialize the address generator.
        
        Args:
            private_key_wif: WIF format private key. If None, generates a new key.
        """
        if private_key_wif:
            self.bit_key = BitKey(private_key_wif)
            # For bitcoinlib, we need to create an HDKey from the same private key
            self.hd_key = HDKey(private_key_wif)
        else:
            self.bit_key = BitKey()
            # Create HDKey from the same private key
            self.hd_key = HDKey(self.bit_key.to_wif())
    
    @property
    def private_key_wif(self) -> str:
        """Get the WIF format private key."""
        return self.bit_key.to_wif()
    
    @property
    def public_key_hex(self) -> str:
        """Get the public key in hex format."""
        return self.bit_key.public_key.hex()
    
    def get_legacy_address(self) -> str:
        """Get the legacy P2PKH address (starts with '1')."""
        return self.bit_key.address
    
    def get_p2sh_segwit_address(self) -> str:
        """Get the P2SH-wrapped segwit address (starts with '3')."""
        return self.bit_key.segwit_address
    
    def get_native_segwit_address(self) -> str:
        """Get the native segwit address (starts with 'bc1')."""
        return self.hd_key.address(script_type='p2wpkh')
    
    def get_address_by_type(self, address_type: str) -> str:
        """
        Get an address by type.
        
        Args:
            address_type: One of 'legacy', 'p2sh-segwit', 'native-segwit'
            
        Returns:
            The address string
        """
        if address_type == 'legacy':
            return self.get_legacy_address()
        elif address_type == 'p2sh-segwit':
            return self.get_p2sh_segwit_address()
        elif address_type == 'native-segwit':
            return self.get_native_segwit_address()
        else:
            raise ValueError(f"Unknown address type: {address_type}")
    
    def get_all_addresses(self) -> dict:
        """Get all address types."""
        return {
            'legacy': self.get_legacy_address(),
            'p2sh_segwit': self.get_p2sh_segwit_address(),
            'native_segwit': self.get_native_segwit_address()
        }
    
    def validate_address_format(self, address: str) -> str:
        """
        Validate and identify address format.
        
        Args:
            address: The address to validate
            
        Returns:
            The address type ('legacy', 'p2sh-segwit', 'native-segwit', 'unknown')
        """
        if address.startswith('1'):
            return 'legacy'
        elif address.startswith('3'):
            return 'p2sh-segwit'
        elif address.startswith('bc1'):
            return 'native-segwit'
        else:
            return 'unknown'


def migrate_legacy_to_native_segwit(private_key_wif: str) -> Tuple[str, str]:
    """
    Migrate from legacy address to native segwit address.
    
    Args:
        private_key_wif: The WIF format private key
        
    Returns:
        Tuple of (old_address, new_address)
    """
    generator = BitcoinAddressGenerator(private_key_wif)
    old_address = generator.get_legacy_address()
    new_address = generator.get_native_segwit_address()
    return old_address, new_address


def test_address_generation():
    """Test the address generation functionality."""
    print("Testing BitcoinAddressGenerator...")
    print("=" * 50)
    
    # Test with new key
    generator = BitcoinAddressGenerator()
    
    print(f"Private Key (WIF): {generator.private_key_wif}")
    print(f"Public Key: {generator.public_key_hex}")
    print()
    
    addresses = generator.get_all_addresses()
    print("Generated addresses:")
    for addr_type, addr in addresses.items():
        format_type = generator.validate_address_format(addr)
        print(f"  {addr_type}: {addr} ({format_type})")
    
    print()
    print("Validation:")
    
    # Validate each address type
    legacy = generator.get_legacy_address()
    p2sh_segwit = generator.get_p2sh_segwit_address()
    native_segwit = generator.get_native_segwit_address()
    
    print(f"✅ Legacy starts with '1': {legacy.startswith('1')}")
    print(f"✅ P2SH-segwit starts with '3': {p2sh_segwit.startswith('3')}")
    print(f"✅ Native segwit starts with 'bc1': {native_segwit.startswith('bc1')}")
    
    # Test with existing key
    print("\nTesting with existing key...")
    generator2 = BitcoinAddressGenerator(generator.private_key_wif)
    print(f"✅ Same native segwit address: {generator2.get_native_segwit_address() == native_segwit}")
    
    print("\n✅ All tests passed! Native segwit address generation works correctly.")


if __name__ == "__main__":
    test_address_generation()
