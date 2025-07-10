#!/usr/bin/env python3
"""
Test script to verify wallet management fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.bitcoin_service import BitcoinService
import time

def test_wallet_management():
    """Test the wallet management functionality"""
    print("🧪 Testing Bitcoin Wallet Management...")
    
    # Create service
    service = BitcoinService()
    
    # Test connection
    print("\n1. Testing Bitcoin node connection...")
    if service.connect_to_node():
        print("✅ Connected to Bitcoin node")
        
        # Test wallet loading
        print("\n2. Testing wallet management...")
        wallet_loaded = service.ensure_wallet_loaded()
        if wallet_loaded:
            print("✅ Wallet is loaded and ready for transactions")
        else:
            print("⚠️ No wallet could be loaded")
        
        # Test fee estimation
        print("\n3. Testing fee estimation...")
        fee_data = service.estimate_fee(6)
        if fee_data:
            print(f"✅ Fee estimation working: {fee_data}")
        else:
            print("⚠️ Fee estimation failed (may be normal if node is busy)")
        
        # Test address monitoring
        print("\n4. Testing address monitoring...")
        test_address = "bc1qyd9gdhsk9952dylkrw9c3tktve38d4lewj6t5s"
        service.add_address_to_monitor(test_address)
        print(f"✅ Monitoring address: {test_address}")
        
        # Wait for a bit to see monitoring results
        print("\n5. Waiting for monitoring results...")
        time.sleep(10)
        
        service.disconnect_from_node()
        print("✅ Disconnected successfully")
        
    else:
        print("❌ Could not connect to Bitcoin node")
        print("Make sure Bitcoin Core is running with RPC enabled")

if __name__ == "__main__":
    test_wallet_management()
