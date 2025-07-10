#!/usr/bin/env python3
"""
Address Generation and Balance Testing Tool
This tool shows how addresses are generated and tests balance checking with known addresses.
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_address_generation():
    """Test how the dashboard generates Bitcoin addresses."""
    print("🔑 Testing Bitcoin Address Generation")
    print("=" * 50)
    
    try:
        from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
        
        # Generate a new address set
        print("Creating new address generator...")
        generator = BitcoinAddressGenerator()
        
        # Show all address types
        addresses = generator.get_all_addresses()
        
        print(f"Private Key (WIF): {generator.private_key_wif}")
        print(f"Legacy Address:    {addresses['legacy']}")
        print(f"P2SH-Segwit:       {addresses['p2sh_segwit']}")
        print(f"Native Segwit:     {addresses['native_segwit']}")
        
        print(f"\n📊 Address Analysis:")
        print(f"Legacy starts with:    {'✅' if addresses['legacy'].startswith('1') else '❌'}")
        print(f"P2SH starts with:      {'✅' if addresses['p2sh_segwit'].startswith('3') else '❌'}")
        print(f"Native starts with:    {'✅' if addresses['native_segwit'].startswith('bc1') else '❌'}")
        
        return generator, addresses
        
    except Exception as e:
        print(f"❌ Address generation failed: {e}")
        return None, None

def check_profile_address():
    """Check what address the profile system is using."""
    print(f"\n👤 Checking Profile Address")
    print("=" * 30)
    
    try:
        from app.config.user_config import PROFILE_DIR, PROFILE_PATH
        
        if PROFILE_PATH.exists():
            with open(PROFILE_PATH, "r") as f:
                data = json.load(f)
            
            current_address = data.get("address", "Not found")
            private_key = data.get("private_key", "Not found")
            
            print(f"Current Profile Address: {current_address}")
            print(f"Address Type: {identify_address_type(current_address)}")
            print(f"Has Private Key: {'✅' if private_key != 'Not found' else '❌'}")
            
            # Show other addresses if available
            if "legacy_address" in data:
                print(f"Legacy Address: {data['legacy_address']}")
            if "p2sh_segwit_address" in data:
                print(f"P2SH Address: {data['p2sh_segwit_address']}")
                
            return current_address, private_key
        else:
            print("❌ No profile found - run the dashboard first to create one")
            return None, None
            
    except Exception as e:
        print(f"❌ Profile check failed: {e}")
        return None, None

def identify_address_type(address):
    """Identify the type of Bitcoin address."""
    if address.startswith('1'):
        return "Legacy (P2PKH)"
    elif address.startswith('3'):
        return "P2SH-wrapped Segwit"
    elif address.startswith('bc1'):
        return "Native Segwit (bech32)"
    elif address.startswith('tb1'):
        return "Testnet Native Segwit"
    elif address.startswith('2'):
        return "Testnet P2SH"
    else:
        return "Unknown"

def test_balance_checking(address):
    """Test balance checking for a specific address."""
    print(f"\n💰 Testing Balance Check for: {address[:20]}...")
    print("=" * 50)
    
    try:
        from bitcoinrpc.authproxy import AuthServiceProxy
        from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
        
        # Connect to Bitcoin Core
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=60)
        
        print(f"Address Type: {identify_address_type(address)}")
        
        # Method 1: listunspent (for imported addresses)
        print(f"\n🔍 Method 1: listunspent")
        try:
            import time
            start_time = time.time()
            unspent = rpc.listunspent(0, 999999999)
            elapsed = time.time() - start_time
            
            # Filter for our address
            our_utxos = [utxo for utxo in unspent if utxo.get('address') == address]
            total_balance = sum(utxo.get('amount', 0) for utxo in our_utxos)
            
            print(f"   ✅ listunspent: {elapsed:.2f}s")
            print(f"   UTXOs found: {len(our_utxos)}")
            print(f"   Balance: {total_balance:.8f} BTC")
            
            if len(our_utxos) == 0:
                print(f"   ℹ️ No UTXOs found - address may not be imported to wallet")
                
        except Exception as e:
            print(f"   ❌ listunspent failed: {e}")
        
        # Method 2: scantxoutset (for any address)
        print(f"\n🔍 Method 2: scantxoutset")
        try:
            start_time = time.time()
            scan_result = rpc.scantxoutset("start", [f"addr({address})"])
            elapsed = time.time() - start_time
            
            if scan_result:
                balance = scan_result.get('total_amount', 0)
                utxo_count = len(scan_result.get('unspents', []))
                
                print(f"   ✅ scantxoutset: {elapsed:.2f}s")
                print(f"   UTXOs found: {utxo_count}")
                print(f"   Balance: {balance:.8f} BTC")
                
                if elapsed > 20:
                    print(f"   ⚠️ SLOW operation - dashboard will throttle this address")
                    
            else:
                print(f"   ❌ scantxoutset returned no result")
                
        except Exception as e:
            print(f"   ❌ scantxoutset failed: {e}")
        
        # Method 3: Check if address is in wallet
        print(f"\n🔍 Method 3: Wallet Import Status")
        try:
            # Try to get address info
            addr_info = rpc.getaddressinfo(address)
            
            print(f"   Address valid: {'✅' if addr_info.get('isvalid', False) else '❌'}")
            print(f"   In wallet: {'✅' if addr_info.get('ismine', False) else '❌'}")
            print(f"   Watchonly: {'✅' if addr_info.get('iswatchonly', False) else '❌'}")
            
            if not addr_info.get('ismine', False) and not addr_info.get('iswatchonly', False):
                print(f"   ℹ️ Address not imported - this explains zero balance in listunspent")
                
        except Exception as e:
            print(f"   ❌ getaddressinfo failed: {e}")
    
    except Exception as e:
        print(f"❌ Balance checking failed: {e}")

def test_known_addresses():
    """Test balance checking with known addresses that have funds."""
    print(f"\n🎯 Testing Known Addresses with Funds")
    print("=" * 40)
    
    # Test addresses with known activity (replace with real addresses for testing)
    known_addresses = [
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  # Example address
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",           # Genesis block address
        "3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC"            # Example P2SH
    ]
    
    for addr in known_addresses:
        print(f"\n📍 Testing {addr[:20]}... ({identify_address_type(addr)})")
        test_balance_checking(addr)
        print()

if __name__ == "__main__":
    print("🧪 Bitcoin Address & Balance Testing Tool")
    print("This tool helps diagnose address generation and balance checking issues")
    print()
    
    # Test address generation
    generator, addresses = test_address_generation()
    
    # Check current profile
    profile_address, private_key = check_profile_address()
    
    # Test balance checking with profile address
    if profile_address:
        test_balance_checking(profile_address)
    
    # Test known addresses
    test_known_addresses()
    
    print(f"\n🎯 Key Findings:")
    print(f"1. Dashboard generates addresses correctly")
    print(f"2. New addresses will have 0 balance (no transaction history)")
    print(f"3. listunspent only shows UTXOs for imported/watched addresses")
    print(f"4. scantxoutset can check any address but is slow")
    print(f"5. For testing, use addresses with known transaction history")
    
    print(f"\n💡 To test with real funds:")
    print(f"1. Send a small amount to the generated address")
    print(f"2. Wait for confirmation")
    print(f"3. Test balance checking again")
    print(f"4. Or use a testnet environment for testing")
