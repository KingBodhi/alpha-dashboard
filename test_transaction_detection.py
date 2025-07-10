#!/usr/bin/env python3
"""
Quick diagnostic script to check transaction detection for a specific address
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.bitcoin_service import BitcoinService
import time

def test_transaction_detection():
    """Test transaction detection for a specific address"""
    print("🔍 Testing Bitcoin transaction detection...")
    
    # Get the address from the profile
    try:
        import json
        from pathlib import Path
        profile_path = Path.home() / ".alpha_protocol_network" / "profile.json"
        
        with open(profile_path, 'r') as f:
            profile = json.load(f)
            test_address = profile.get('address')
        
        if not test_address:
            print("❌ No address found in profile")
            return
            
        print(f"📍 Testing address: {test_address}")
        
        # Create service and connect
        service = BitcoinService()
        
        if not service.connect_to_node():
            print("❌ Could not connect to Bitcoin node")
            return
        
        print("✅ Connected to Bitcoin node")
        
        # Force address import for better detection
        try:
            import_result = service._safe_rpc_call(lambda: service.rpc_connection.importaddress(test_address, f"test_{test_address[:8]}", False))
            print(f"✅ Address imported successfully")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Address already imported")
            else:
                print(f"⚠️ Could not import address: {e}")
        
        # Test balance detection
        print("\n1. Testing balance detection...")
        service.update_address_balance(test_address)
        balance = service.address_balances.get(test_address, 0)
        print(f"📊 Current balance: {balance:.8f} BTC")
        
        # Test transaction detection
        print("\n2. Testing transaction detection...")
        service.update_address_transactions(test_address)
        transactions = service.address_transactions.get(test_address, [])
        print(f"📋 Found transactions: {len(transactions)}")
        
        for i, tx in enumerate(transactions[:5]):  # Show first 5
            print(f"  {i+1}. {tx.get('txid', 'Unknown')[:16]}... - {tx.get('amount', 0):.8f} BTC ({tx.get('type', 'unknown')})")
        
        # Test wallet transactions
        print("\n3. Testing wallet transaction list...")
        try:
            wallet_txs = service._safe_rpc_call(lambda: service.rpc_connection.listtransactions("*", 100))
            if wallet_txs:
                print(f"📋 Total wallet transactions: {len(wallet_txs)}")
                
                # Filter for our address
                our_txs = [tx for tx in wallet_txs if tx.get('address') == test_address]
                print(f"📋 Transactions for our address: {len(our_txs)}")
                
                for tx in our_txs[:3]:  # Show first 3
                    print(f"  - {tx.get('txid', 'Unknown')[:16]}... - {tx.get('amount', 0):.8f} BTC ({tx.get('category', 'unknown')})")
            else:
                print("⚠️ No wallet transactions found")
        except Exception as e:
            print(f"⚠️ Could not get wallet transactions: {e}")
        
        # Test recent blocks scanning
        print("\n4. Testing recent block scanning...")
        try:
            best_hash = service._safe_rpc_call(lambda: service.rpc_connection.getbestblockhash())
            if best_hash:
                print(f"📦 Latest block: {best_hash[:16]}...")
                
                # Get the latest block
                block = service._safe_rpc_call(lambda: service.rpc_connection.getblock(best_hash, 2))
                if block:
                    print(f"📦 Block height: {block.get('height', 'unknown')}")
                    print(f"📦 Transactions in block: {len(block.get('tx', []))}")
                    
                    # Check if any transaction involves our address
                    found_in_block = False
                    for tx in block.get('tx', []):
                        for vout in tx.get('vout', []):
                            script_pub_key = vout.get('scriptPubKey', {})
                            addresses = script_pub_key.get('addresses', [])
                            if 'address' in script_pub_key:
                                addresses.append(script_pub_key['address'])
                            
                            if test_address in addresses:
                                found_in_block = True
                                print(f"  ✅ Found transaction involving our address: {tx.get('txid', 'Unknown')[:16]}...")
                                break
                        if found_in_block:
                            break
                    
                    if not found_in_block:
                        print(f"  📍 No transactions for our address in latest block")
                        
        except Exception as e:
            print(f"⚠️ Could not scan recent blocks: {e}")
        
        service.disconnect()
        print("\n✅ Diagnostic complete")
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")

if __name__ == "__main__":
    test_transaction_detection()
