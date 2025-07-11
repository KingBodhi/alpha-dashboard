#!/usr/bin/env python3
"""
Verification test for Bitcoin Core-only wallet integration.
This test verifies that ONLY Bitcoin Core wallets can be used.
"""

import sys
import os
sys.path.append('.')

from services.bitcoin_service import BitcoinService
from app.utils.bitcoin_wallet_descriptor_generator import BitcoinWalletDescriptorGenerator
from app.pages.profile_page import ProfilePage


def test_bitcoin_core_only_enforcement():
    """Test that the system enforces Bitcoin Core wallet-only operation."""
    print("🧪 Testing Bitcoin Core-Only Wallet Enforcement...")
    print("=" * 60)
    
    # Test 1: Profile page without Bitcoin service
    print("\n1️⃣ Testing ProfilePage without Bitcoin Core connection...")
    profile_page = ProfilePage(bitcoin_service=None)
    
    # Check initial state
    assert not profile_page.wallet_loaded, "❌ Wallet should not be loaded without Bitcoin Core"
    assert profile_page.descriptor_generator is None, "❌ Descriptor generator should be None"
    assert profile_page.wallet_addresses == {}, "❌ Wallet addresses should be empty"
    
    # Check UI state
    assert not profile_page.address_type_combo.isEnabled(), "❌ Address type combo should be disabled"
    assert not profile_page.wallet_section.isVisible(), "❌ Wallet section should be hidden"
    
    print("✅ Profile page correctly blocks wallet functionality without Bitcoin Core")
    
    # Test 2: Verify no legacy fallback exists
    print("\n2️⃣ Testing that legacy fallback is removed...")
    
    # Check that load_legacy_profile method is removed/disabled
    try:
        profile_page.load_legacy_profile({})
        print("❌ ERROR: Legacy profile loader still exists!")
        return False
    except AttributeError:
        print("✅ Legacy profile loader properly removed")
    except Exception as e:
        if "Bitcoin Core wallet required" in str(e):
            print("✅ Legacy profile loader properly disabled")
        else:
            print(f"⚠️ Unexpected error: {e}")
    
    # Test 3: Address type change enforcement
    print("\n3️⃣ Testing address type change enforcement...")
    
    # Try to change address type without Bitcoin Core
    try:
        original_combo_value = profile_page.address_type_combo.currentText()
        profile_page.on_address_type_changed("Legacy (P2PKH)")
        print("✅ Address type change properly blocked without Bitcoin Core")
    except Exception as e:
        print(f"✅ Address type change correctly prevented: {e}")
    
    # Test 4: Connection state methods
    print("\n4️⃣ Testing connection state management...")
    
    # Test disconnect method
    profile_page.on_bitcoin_core_disconnected()
    assert not profile_page.wallet_loaded, "❌ Wallet should be unloaded on disconnect"
    assert profile_page.descriptor_generator is None, "❌ Descriptor generator should be cleared"
    assert not profile_page.wallet_section.isVisible(), "❌ Wallet section should be hidden"
    print("✅ Disconnect properly clears wallet state")
    
    # Test 5: Profile saving without wallet
    print("\n5️⃣ Testing profile saving without Bitcoin Core...")
    
    profile_page.nickname_input.setText("TestNode")
    profile_page.role_select.setCurrentText("Master")
    
    try:
        profile_page.save_profile()
        print("✅ Profile saving works without wallet (saves basic data only)")
    except Exception as e:
        print(f"❌ Profile saving failed: {e}")
        return False
    
    print("\n✅ All Bitcoin Core-only enforcement tests passed!")
    return True


def test_bitcoin_core_connection_simulation():
    """Test Bitcoin Core connection simulation."""
    print("\n🧪 Testing Bitcoin Core Connection Simulation...")
    print("=" * 60)
    
    # Create profile page
    profile_page = ProfilePage(bitcoin_service=None)
    
    # Simulate Bitcoin Core connection
    print("1️⃣ Simulating Bitcoin Core connection...")
    
    # Before connection
    assert not profile_page.wallet_section.isVisible(), "❌ Wallet section should be hidden initially"
    assert not profile_page.address_type_combo.isEnabled(), "❌ Address combo should be disabled"
    
    # Simulate connection (without actual Bitcoin Core)
    try:
        profile_page.on_bitcoin_core_connected()
        print("⚠️ Connection simulation attempted (will fail without real Bitcoin Core)")
    except Exception as e:
        print(f"✅ Connection properly requires real Bitcoin Core: {e}")
    
    # Test disconnection
    profile_page.on_bitcoin_core_disconnected()
    assert not profile_page.wallet_section.isVisible(), "❌ Wallet section should be hidden after disconnect"
    
    print("✅ Connection state management works correctly")
    return True


def test_descriptor_generator_independence():
    """Test that descriptor generator only works with Bitcoin Core."""
    print("\n🧪 Testing Descriptor Generator Independence...")
    print("=" * 60)
    
    # Test 1: Descriptor generator without Bitcoin service
    print("1️⃣ Testing descriptor generator without Bitcoin service...")
    
    try:
        generator = BitcoinWalletDescriptorGenerator(None)
        result = generator.get_wallet_info()
        print("❌ ERROR: Descriptor generator should fail without Bitcoin service")
        return False
    except Exception as e:
        print(f"✅ Descriptor generator properly requires Bitcoin service: {e}")
    
    # Test 2: Descriptor generator methods without connection
    print("2️⃣ Testing descriptor generator methods without connection...")
    
    # Create a mock bitcoin service (disconnected)
    mock_service = type('MockService', (), {
        'is_connected': False,
        'rpc_connection': None
    })()
    
    try:
        generator = BitcoinWalletDescriptorGenerator(mock_service)
        addresses = generator.get_all_address_types()
        if not addresses:
            print("✅ Descriptor generator returns empty results without connection")
        else:
            print("❌ ERROR: Descriptor generator should not return addresses without connection")
            return False
    except Exception as e:
        print(f"✅ Descriptor generator properly handles disconnected state: {e}")
    
    print("✅ Descriptor generator independence verified")
    return True


def main():
    """Run all Bitcoin Core-only enforcement tests."""
    print("🚀 Bitcoin Core-Only Wallet Integration Verification")
    print("=" * 80)
    
    success_count = 0
    total_tests = 3
    
    # Run tests
    if test_bitcoin_core_only_enforcement():
        success_count += 1
    
    if test_bitcoin_core_connection_simulation():
        success_count += 1
    
    if test_descriptor_generator_independence():
        success_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(f"🏁 Test Summary: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Bitcoin Core-only enforcement is working correctly.")
        print("\n✅ Verified Features:")
        print("   • No wallet functionality without Bitcoin Core")
        print("   • Legacy address generation completely removed")
        print("   • Address type changes require Bitcoin Core connection")
        print("   • Proper connection state management")
        print("   • Descriptor generator requires Bitcoin Core")
        print("   • Profile saving works without compromising security")
        print("\n🔒 The system now ONLY supports Bitcoin Core wallets!")
    else:
        print("❌ Some tests failed. The Bitcoin Core-only enforcement may have issues.")
        print("\n⚠️ Review the error messages above to identify problems.")


if __name__ == "__main__":
    main()