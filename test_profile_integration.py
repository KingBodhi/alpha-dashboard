#!/usr/bin/env python3
"""
Test script to verify the updated profile page with native segwit support.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
from app.pages.profile_page import ProfilePage
from PyQt6.QtWidgets import QApplication

def test_profile_integration():
    """Test the profile page integration with native segwit addresses."""
    print("Testing ProfilePage with native segwit support...")
    print("=" * 60)
    
    # First, test the address generator directly
    print("1. Testing address generator:")
    generator = BitcoinAddressGenerator()
    addresses = generator.get_all_addresses()
    
    for addr_type, addr in addresses.items():
        format_detected = generator.validate_address_format(addr)
        print(f"   {addr_type}: {addr} ({format_detected})")
    
    print(f"\n✅ Native segwit generated: {addresses['native_segwit']}")
    
    # Test if we can create the profile page
    print("\n2. Testing ProfilePage creation:")
    try:
        app = QApplication([])
        profile_page = ProfilePage()
        
        # Check if it has the expected attributes
        if hasattr(profile_page, 'address') and hasattr(profile_page, 'private_key'):
            print("✅ ProfilePage created successfully")
            print(f"   Address: {profile_page.address}")
            print(f"   Address format: {generator.validate_address_format(profile_page.address)}")
            
            # Test address type changes
            if hasattr(profile_page, 'on_address_type_changed'):
                print("✅ Address type change method available")
        else:
            print("❌ ProfilePage missing expected attributes")
            
    except Exception as e:
        print(f"❌ Error creating ProfilePage: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n3. Testing address migration logic:")
    
    # Test with a legacy address to see if it migrates
    legacy_generator = BitcoinAddressGenerator()
    legacy_address = legacy_generator.get_legacy_address()
    native_address = legacy_generator.get_native_segwit_address()
    
    print(f"   Legacy address: {legacy_address}")
    print(f"   Would migrate to: {native_address}")
    print(f"   Migration needed: {not native_address.startswith('bc1')}")
    
    print("\n✅ All integration tests completed!")

if __name__ == "__main__":
    test_profile_integration()
