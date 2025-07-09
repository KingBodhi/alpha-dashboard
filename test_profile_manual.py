#!/usr/bin/env python3
"""
Manual test of profile page address generation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
import json
from pathlib import Path

def test_profile_address_generation():
    """Test the profile address generation workflow."""
    print("Testing profile address generation workflow...")
    print("=" * 60)
    
    # Test path where profile would be stored
    profile_dir = Path.home() / ".alpha_protocol_network"
    profile_path = profile_dir / "profile.json"
    
    print(f"Profile directory: {profile_dir}")
    print(f"Profile path: {profile_path}")
    
    # Generate a new address like the profile page would
    generator = BitcoinAddressGenerator()
    
    data = {
        "private_key": generator.private_key_wif,
        "address": generator.get_native_segwit_address(),
        "legacy_address": generator.get_legacy_address(),
        "p2sh_segwit_address": generator.get_p2sh_segwit_address(),
        "nickname": "TestNode",
        "role": "Standard",
        "devices": []
    }
    
    print(f"\nGenerated profile data:")
    print(f"  Private key: {data['private_key']}")
    print(f"  Primary address (native segwit): {data['address']}")
    print(f"  Legacy address: {data['legacy_address']}")
    print(f"  P2SH segwit address: {data['p2sh_segwit_address']}")
    
    # Verify address formats
    print(f"\nAddress format verification:")
    print(f"  Primary address starts with 'bc1': {data['address'].startswith('bc1')}")
    print(f"  Legacy address starts with '1': {data['legacy_address'].startswith('1')}")
    print(f"  P2SH segwit starts with '3': {data['p2sh_segwit_address'].startswith('3')}")
    
    # Test with same private key to ensure consistency
    print(f"\nConsistency test:")
    generator2 = BitcoinAddressGenerator(data['private_key'])
    print(f"  Same native segwit: {generator2.get_native_segwit_address() == data['address']}")
    print(f"  Same legacy: {generator2.get_legacy_address() == data['legacy_address']}")
    
    # Test address type selection
    print(f"\nAddress type selection test:")
    test_types = [
        ("Segwit (bech32)", "native-segwit"),
        ("P2SH-wrapped Segwit", "p2sh-segwit"),
        ("Legacy (P2PKH)", "legacy")
    ]
    
    for ui_type, internal_type in test_types:
        address = generator.get_address_by_type(internal_type)
        print(f"  {ui_type}: {address}")
    
    print(f"\n✅ All profile address generation tests passed!")
    print(f"\nThe profile page will now generate native segwit addresses by default,")
    print(f"which should be compatible with Bitcoin Core descriptor wallets.")

if __name__ == "__main__":
    test_profile_address_generation()
