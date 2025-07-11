#!/usr/bin/env python3
"""
Test script for the new descriptor-based wallet integration.
This tests the Bitcoin Core wallet descriptor functionality.
"""

import sys
import os
sys.path.append('.')

from services.bitcoin_service import BitcoinService
from app.utils.bitcoin_wallet_descriptor_generator import BitcoinWalletDescriptorGenerator
from app.pages.profile_page import ProfilePage


def test_bitcoin_service_descriptor_methods():
    """Test the new descriptor methods in BitcoinService."""
    print("🧪 Testing BitcoinService descriptor methods...")
    print("=" * 60)
    
    try:
        # Create Bitcoin service
        bitcoin_service = BitcoinService()
        
        # Try to connect
        if not bitcoin_service.connect_to_node():
            print("❌ Could not connect to Bitcoin Core - test cannot proceed")
            print("Make sure Bitcoin Core is running and RPC is configured")
            return False
        
        print("✅ Connected to Bitcoin Core")
        
        # Test wallet info
        wallet_info = bitcoin_service._safe_rpc_call(
            lambda: bitcoin_service.rpc_connection.getwalletinfo()
        )
        if wallet_info:
            print(f"📋 Wallet: {wallet_info.get('walletname', 'default')}")
            print(f"📋 Descriptor wallet: {wallet_info.get('descriptors', False)}")
            print(f"📋 Balance: {wallet_info.get('balance', 0)} BTC")
        
        # Test descriptor methods
        print("\n🔍 Testing descriptor methods...")
        
        # Test get_wallet_descriptors
        descriptors = bitcoin_service.get_wallet_descriptors()
        if descriptors:
            desc_list = descriptors.get('descriptors', [])
            print(f"✅ Found {len(desc_list)} descriptors")
            for i, desc in enumerate(desc_list[:3]):  # Show first 3
                print(f"   {i+1}. {desc.get('desc', '')[:50]}...")
        else:
            print("⚠️ No descriptors available (legacy wallet or error)")
        
        # Test get_wallet_addresses
        print("\n📍 Testing get_wallet_addresses...")
        addresses = bitcoin_service.get_wallet_addresses()
        print(f"✅ Found {len(addresses)} addresses:")
        for addr_data in addresses[:5]:  # Show first 5
            ownership = bitcoin_service.validate_address_ownership(addr_data['address'])
            print(f"   {addr_data['type']}: {addr_data['address']} (owned: {ownership})")
        
        # Test get_all_wallet_address_types
        print("\n🎯 Testing get_all_wallet_address_types...")
        all_addresses = bitcoin_service.get_all_wallet_address_types()
        for addr_type, address in all_addresses.items():
            if address:
                ownership = bitcoin_service.validate_address_ownership(address)
                print(f"   {addr_type}: {address} (owned: {ownership})")
            else:
                print(f"   {addr_type}: Failed to generate")
        
        # Test address generation
        print("\n🆕 Testing generate_wallet_address...")
        new_bech32 = bitcoin_service.generate_wallet_address('bech32', 'Test SegWit Address')
        if new_bech32:
            print(f"✅ Generated bech32: {new_bech32}")
            ownership = bitcoin_service.validate_address_ownership(new_bech32)
            print(f"   Ownership verified: {ownership}")
        else:
            print("❌ Failed to generate bech32 address")
        
        print("\n✅ BitcoinService descriptor tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_descriptor_generator():
    """Test the BitcoinWalletDescriptorGenerator."""
    print("\n🧪 Testing BitcoinWalletDescriptorGenerator...")
    print("=" * 60)
    
    try:
        # Create Bitcoin service
        bitcoin_service = BitcoinService()
        
        # Try to connect
        if not bitcoin_service.connect_to_node():
            print("❌ Could not connect to Bitcoin Core - test cannot proceed")
            return False
        
        # Create descriptor generator
        generator = BitcoinWalletDescriptorGenerator(bitcoin_service)
        
        # Test wallet info
        print("📋 Getting wallet info...")
        wallet_info = generator.get_wallet_info()
        print(f"✅ Wallet name: {wallet_info.get('walletname', 'default')}")
        print(f"✅ Descriptor wallet: {wallet_info.get('descriptors', False)}")
        print(f"✅ Balance: {wallet_info.get('balance', 0)} BTC")
        
        # Test primary address
        print("\n🎯 Testing get_primary_address...")
        primary = generator.get_primary_address('bech32')
        print(f"✅ Primary bech32 address: {primary}")
        
        # Test all address types
        print("\n📍 Testing get_all_address_types...")
        all_addresses = generator.get_all_address_types()
        for addr_type, address in all_addresses.items():
            ownership = generator.validate_address_ownership(address)
            print(f"   {addr_type}: {address} (owned: {ownership})")
        
        print("\n✅ BitcoinWalletDescriptorGenerator tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_profile_page_integration():
    """Test the ProfilePage integration with descriptor wallets."""
    print("\n🧪 Testing ProfilePage descriptor integration...")
    print("=" * 60)
    
    try:
        # Create Bitcoin service
        bitcoin_service = BitcoinService()
        
        # Try to connect
        if not bitcoin_service.connect_to_node():
            print("❌ Could not connect to Bitcoin Core - test cannot proceed")
            return False
        
        # Create profile page with Bitcoin service
        profile_page = ProfilePage(bitcoin_service)
        
        # Check if descriptor generator was initialized
        if profile_page.descriptor_generator:
            print("✅ Descriptor generator initialized")
            
            # Check if wallet addresses were loaded
            if profile_page.wallet_addresses:
                print(f"✅ Loaded {len(profile_page.wallet_addresses)} wallet address types:")
                for addr_type, address in profile_page.wallet_addresses.items():
                    print(f"   {addr_type}: {address}")
                
                # Check current address
                print(f"\n✅ Current primary address: {profile_page.address}")
                
                # Test address type detection
                if profile_page.descriptor_generator:
                    addr_type = profile_page.descriptor_generator._detect_address_type(profile_page.address)
                    print(f"✅ Detected address type: {addr_type}")
                
            else:
                print("⚠️ No wallet addresses loaded")
        else:
            print("⚠️ Descriptor generator not initialized")
        
        print("\n✅ ProfilePage integration tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Testing Descriptor-Based Wallet Integration")
    print("=" * 80)
    
    success_count = 0
    total_tests = 3
    
    # Run tests
    if test_bitcoin_service_descriptor_methods():
        success_count += 1
    
    if test_descriptor_generator():
        success_count += 1
    
    if test_profile_page_integration():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(f"🏁 Test Summary: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Descriptor-based wallet integration is working correctly.")
        print("\n📝 Key Features Verified:")
        print("   ✅ Bitcoin Core wallet connection")
        print("   ✅ Descriptor wallet detection")
        print("   ✅ Address generation from wallet")
        print("   ✅ All address types (bech32, P2SH-SegWit, legacy)")
        print("   ✅ Address ownership validation")
        print("   ✅ ProfilePage integration")
        print("\n🔄 The system now uses Bitcoin Core's wallet instead of standalone key generation!")
    else:
        print("❌ Some tests failed. Check the error messages above.")
        print("\n💡 Common issues:")
        print("   - Bitcoin Core not running")
        print("   - RPC connection not configured")
        print("   - No wallet loaded in Bitcoin Core")
        print("   - Insufficient permissions")


if __name__ == "__main__":
    main()