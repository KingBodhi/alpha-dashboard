#!/usr/bin/env python3
"""Test transaction functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from services.bitcoin_service import BitcoinService
from app.pages.transaction_page import TransactionPage
from PyQt6.QtWidgets import QApplication
import time

def test_transaction_functionality():
    """Test transaction page and service integration."""
    print("🧪 Testing Transaction Functionality...")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create service and transaction page
    service = BitcoinService()
    transaction_page = TransactionPage()
    
    # Test service integration
    print("\n🔗 Testing service integration...")
    transaction_page.set_bitcoin_service(service)
    transaction_page.set_wallet_address("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
    print("✅ Service and address connected to transaction page")
    
    # Test fee estimation
    print("\n💰 Testing fee estimation...")
    if service.connect_to_node():
        print("✅ Connected to Bitcoin node")
        
        # Test fee estimation
        fee_info = service.estimate_fee(6)
        if fee_info:
            print(f"✅ Fee estimation: {fee_info}")
        else:
            print("⚠️ Fee estimation not available")
        
        # Test transaction creation components
        print("\n🔄 Testing transaction creation...")
        test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
        utxos = service.get_unspent_outputs(test_address)
        print(f"✅ Found {len(utxos)} UTXOs for address")
        
        # Test raw transaction creation (without broadcasting)
        if utxos:
            print("\n🔨 Testing raw transaction creation...")
            inputs = [{"txid": utxos[0]["txid"], "vout": utxos[0]["vout"]}]
            outputs = {"bc1qother": 0.001}
            
            raw_tx = service.create_raw_transaction(inputs, outputs)
            if raw_tx:
                print(f"✅ Created raw transaction: {raw_tx[:50]}...")
            else:
                print("❌ Failed to create raw transaction")
        
        service.disconnect()
        print("🔌 Disconnected from Bitcoin node")
        
    else:
        print("❌ Could not connect to Bitcoin node")
        print("💡 This is expected if Bitcoin Core is not running")
        print("💡 Transaction functionality requires a running Bitcoin Core node")
    
    print("\n🎯 Transaction test completed!")

if __name__ == "__main__":
    test_transaction_functionality()
