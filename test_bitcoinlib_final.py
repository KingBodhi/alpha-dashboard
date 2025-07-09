#!/usr/bin/env python3
"""
Test script to properly test bitcoinlib address generation.
"""

from bitcoinlib.keys import HDKey
from bitcoinlib.encoding import pubkeyhash_to_addr

def test_address_types():
    """Test different address types with bitcoinlib."""
    print("Testing Bitcoin address types with bitcoinlib...")
    print("=" * 60)
    
    # Create a new HDKey
    key = HDKey()
    
    print(f"Private Key WIF: {key.wif}")
    print(f"Public Key: {key.public_hex}")
    print()
    
    # Test different address types
    print("Generated addresses:")
    
    # Legacy address (P2PKH)
    legacy_addr = key.address(script_type='p2pkh')
    print(f"Legacy (P2PKH): {legacy_addr}")
    
    # Native segwit address (P2WPKH - bech32)
    native_segwit_addr = key.address(script_type='p2wpkh')
    print(f"Native Segwit (P2WPKH): {native_segwit_addr}")
    
    # P2SH-wrapped segwit address
    p2sh_segwit_addr = key.address(script_type='p2sh-p2wpkh')
    print(f"P2SH-wrapped Segwit: {p2sh_segwit_addr}")
    
    print()
    print("Address verification:")
    
    addresses = [
        ("Legacy", legacy_addr),
        ("Native Segwit", native_segwit_addr),
        ("P2SH-wrapped", p2sh_segwit_addr)
    ]
    
    for name, addr in addresses:
        if addr.startswith('bc1'):
            print(f"✅ {name}: {addr} (Native Segwit - bech32)")
        elif addr.startswith('3'):
            print(f"⚠️  {name}: {addr} (P2SH)")
        elif addr.startswith('1'):
            print(f"📜 {name}: {addr} (Legacy P2PKH)")
        else:
            print(f"❓ {name}: {addr} (Unknown)")
    
    print()
    print("CONCLUSION:")
    if native_segwit_addr.startswith('bc1'):
        print("✅ bitcoinlib successfully generates native segwit (bech32) addresses!")
        print("   This is exactly what we need for Bitcoin Core compatibility.")
    else:
        print("❌ bitcoinlib did not generate the expected native segwit format.")
    
    return key.wif, native_segwit_addr

if __name__ == "__main__":
    test_address_types()
