#!/usr/bin/env python3
"""
Test script to verify the connection fixes and transaction fetching functionality.
"""

import sys
import time
from services.bitcoin_service import BitcoinService
from PyQt6.QtCore import QCoreApplication

def test_connection_and_transactions():
    """Test Bitcoin Core connection and transaction fetching."""
    print("🧪 Testing Bitcoin Core connection and transaction fetching...")
    print("=" * 60)
    
    # Create Qt application (required for PyQt signals)
    app = QCoreApplication(sys.argv)
    
    # Create Bitcoin service
    service = BitcoinService()
    
    # Set up signal handlers for testing
    connection_status = {'connected': False}
    
    def on_connection_status_changed(connected):
        connection_status['connected'] = connected
        print(f"📡 Connection status: {'Connected ✅' if connected else 'Disconnected ❌'}")
    
    def on_status_message(message):
        print(f"📟 Status: {message}")
    
    def on_error_occurred(error):
        print(f"❌ Error: {error}")
    
    def on_blockchain_info_updated(info):
        print(f"⛓️  Blockchain info: Block {info.get('blocks', 0)}, Chain: {info.get('chain', 'unknown')}")
    
    def on_address_balance_updated(address, balance_info):
        balance = balance_info.get('balance_btc', 0)
        utxos = balance_info.get('utxo_count', 0)
        print(f"💰 Balance for {address[:8]}...: {balance:.8f} BTC ({utxos} UTXOs)")
    
    def on_address_transactions_updated(address, transactions):
        print(f"📋 Transactions for {address[:8]}...: {len(transactions)} found")
        for i, tx in enumerate(transactions[:3]):  # Show first 3 transactions
            print(f"  {i+1}. {tx.get('txid', '')[:16]}... - {tx.get('amount', 0):.8f} BTC ({tx.get('type', 'unknown')})")
    
    # Connect signals
    service.connection_status_changed.connect(on_connection_status_changed)
    service.status_message.connect(on_status_message)
    service.error_occurred.connect(on_error_occurred)
    service.blockchain_info_updated.connect(on_blockchain_info_updated)
    service.address_balance_updated.connect(on_address_balance_updated)
    service.address_transactions_updated.connect(on_address_transactions_updated)
    
    try:
        # Test 1: Connection
        print("\n🔗 Test 1: Connecting to Bitcoin Core...")
        success = service.connect_to_node()
        if success:
            print("✅ Connection successful!")
        else:
            print("❌ Connection failed - checking if running in no-node mode...")
            
        # Test 2: Start monitoring
        print("\n📡 Test 2: Starting monitoring...")
        service.start_monitoring()
        
        # Wait a bit for initial data
        print("\n⏱️  Waiting for initial data...")
        app.processEvents()
        time.sleep(3)
        app.processEvents()
        
        # Test 3: Add a test address for monitoring
        print("\n📍 Test 3: Adding test address for monitoring...")
        # Use a well-known address with some transaction history
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis block address
        service.add_address_to_monitor(test_address)
        
        # Wait for address data to be fetched
        print("⏱️  Waiting for address data...")
        app.processEvents()
        time.sleep(5)
        app.processEvents()
        
        # Test 4: Force an update to test the improved error handling
        print("\n🔄 Test 4: Testing update data functionality...")
        service.update_data()
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        # Test 5: Test address balance update
        print("\n💰 Test 5: Testing address balance update...")
        service.update_address_balance(test_address)
        app.processEvents()
        time.sleep(3)
        app.processEvents()
        
        print("\n✅ All tests completed!")
        print("\nConnection Status Summary:")
        print(f"- Connected to Bitcoin Core: {connection_status['connected']}")
        print(f"- Monitored addresses: {len(service.monitored_addresses)}")
        print(f"- Node busy status: {getattr(service, 'node_busy', False)}")
        print(f"- Failure count: {getattr(service, '_rpc_failure_count', 0)}")
        
        # Test the transaction fetching specifically
        if connection_status['connected']:
            print("\n📋 Test 6: Testing transaction fetching...")
            service.update_address_transactions(test_address)
            app.processEvents()
            time.sleep(3)
            app.processEvents()
    
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🧹 Cleaning up...")
        service.disconnect()
        app.quit()

if __name__ == "__main__":
    test_connection_and_transactions()
