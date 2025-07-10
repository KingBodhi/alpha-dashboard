#!/usr/bin/env python3
"""
Address Mismatch Diagnostic
Identifies why dashboard-generated addresses don't match wallet addresses with funds.
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the Python path  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def find_address_mismatch():
    """Find why dashboard addresses don't match wallet addresses with funds."""
    print("🔍 Dashboard vs Wallet Address Mismatch Diagnostic")
    print("=" * 60)
    
    # 1. Check what address the dashboard generates/uses
    print("🎯 Dashboard Address Generation...")
    try:
        from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
        
        # Generate addresses the same way dashboard does
        generator = BitcoinAddressGenerator()
        addresses = generator.get_all_addresses()
        
        print(f"Dashboard generates these addresses:")
        print(f"  Legacy:      {addresses['legacy']}")
        print(f"  P2SH-Segwit: {addresses['p2sh_segwit']}")  
        print(f"  Native:      {addresses['native_segwit']}")
        print(f"  Default:     {addresses['native_segwit']} (Native Segwit)")
        
    except Exception as e:
        print(f"❌ Dashboard address generation failed: {e}")
        return
    
    # 2. Check if there's an existing profile
    print(f"\n👤 Profile Address Check...")
    try:
        profile_path = Path.home() / ".alpha_protocol_network" / "profile.json"
        
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profile_data = json.load(f)
            
            current_address = profile_data.get('address', 'Not found')
            private_key = profile_data.get('private_key', 'Not found')
            
            print(f"Profile exists:")
            print(f"  Current address: {current_address}")
            print(f"  Address type: {identify_address_type(current_address)}")
            
            # If profile has an address, regenerate all addresses from its private key
            if private_key != 'Not found':
                profile_generator = BitcoinAddressGenerator(private_key)
                profile_addresses = profile_generator.get_all_addresses()
                
                print(f"\nAddresses from profile's private key:")
                print(f"  Legacy:      {profile_addresses['legacy']}")
                print(f"  P2SH-Segwit: {profile_addresses['p2sh_segwit']}")
                print(f"  Native:      {profile_addresses['native_segwit']}")
                
                # Check if current address matches any of these
                if current_address in profile_addresses.values():
                    print(f"✅ Profile address matches generated addresses")
                else:
                    print(f"❌ Profile address doesn't match any generated address!")
                    print(f"   This could be the problem!")
                    
        else:
            print(f"No profile found - dashboard will create new addresses")
            
    except Exception as e:
        print(f"❌ Profile check failed: {e}")
    
    # 3. Manual address input for testing
    print(f"\n🔧 Manual Wallet Address Test")
    print(f"If you know an address that has funds in your wallet, enter it below:")
    print(f"(Press Enter to skip)")
    
    try:
        wallet_address = input("Enter wallet address with funds: ").strip()
        
        if wallet_address:
            print(f"\nTesting wallet address: {wallet_address}")
            print(f"Address type: {identify_address_type(wallet_address)}")
            
            # Test if dashboard's balance checking would work with this address
            test_address_with_dashboard_methods(wallet_address)
            
    except KeyboardInterrupt:
        print(f"\nSkipping manual test...")
    
    # 4. Provide recommendations
    print(f"\n💡 Potential Issues & Solutions:")
    print(f"")
    print(f"🔧 Issue 1: Address Generation Mismatch")
    print(f"   - Dashboard generates new addresses")
    print(f"   - Your wallet has funds in different addresses")
    print(f"   - Solution: Import your wallet's private key to dashboard")
    print(f"")
    print(f"🔧 Issue 2: Wallet Import Problem") 
    print(f"   - Dashboard address not imported to Bitcoin Core wallet")
    print(f"   - Solution: Import dashboard address to Bitcoin Core")
    print(f"")
    print(f"🔧 Issue 3: Descriptor vs Legacy Wallet")
    print(f"   - Different wallet types use different balance checking methods")
    print(f"   - Solution: Ensure dashboard uses correct method for your wallet type")
    print(f"")
    print(f"🎯 Quick Fix:")
    print(f"1. Find address with funds in your Bitcoin Core wallet")
    print(f"2. Export its private key: dumpprivkey <address>")
    print(f"3. Use that private key when setting up dashboard profile")

def identify_address_type(address):
    """Identify Bitcoin address type."""
    if address.startswith('1'):
        return "Legacy (P2PKH)"
    elif address.startswith('3'):
        return "P2SH-wrapped Segwit"
    elif address.startswith('bc1'):
        return "Native Segwit (bech32)"
    elif address.startswith('tb1'):
        return "Testnet Native Segwit"
    else:
        return "Unknown"

def test_address_with_dashboard_methods(address):
    """Test if dashboard methods would work with given address."""
    print(f"\n🧪 Testing Dashboard Methods with Your Address...")
    
    try:
        from services.bitcoin_service import BitcoinService
        
        # Create service and test balance checking
        service = BitcoinService()
        
        print(f"Testing address: {address[:20]}...")
        print(f"Address type: {identify_address_type(address)}")
        
        # Add to monitoring to test
        service.monitored_addresses.add(address)
        print(f"✅ Added to dashboard monitoring")
        
        # Test balance update method
        print(f"🔄 Testing dashboard balance checking...")
        if service.test_connection():
            service.update_address_balance(address)
            print(f"✅ Balance check method completed")
        else:
            print(f"❌ Cannot test - Bitcoin Core not connected")
            print(f"💡 But address format looks valid for dashboard")
            
    except Exception as e:
        print(f"❌ Dashboard method test failed: {e}")

if __name__ == "__main__":
    find_address_mismatch()
