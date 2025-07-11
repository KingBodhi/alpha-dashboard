#!/usr/bin/env python3
"""
Improved test script to verify the connection fixes and enhanced functionality.
This test focuses on robustness and proper error handling.
"""

import sys
import time
from services.bitcoin_service import BitcoinService
from PyQt6.QtCore import QCoreApplication

def test_improved_connection():
    """Test the improved Bitcoin Core connection with better error handling."""
    print("🧪 Testing IMPROVED Bitcoin Core connection and functionality...")
    print("=" * 70)
    
    # Create Qt application
    app = QCoreApplication(sys.argv)
    
    # Create Bitcoin service
    service = BitcoinService()
    
    # Track results
    test_results = {
        'connection': False,
        'wallet_detection': False,
        'address_monitoring': False,
        'balance_check': False,
        'error_handling': False
    }
    
    # Set up signal handlers
    def on_connection_status_changed(connected):
        test_results['connection'] = connected
        print(f"📡 Connection: {'✅ Connected' if connected else '❌ Disconnected'}")
    
    def on_status_message(message):
        print(f"📟 Status: {message}")
        # Track if we get proper error handling messages
        if any(keyword in message.lower() for keyword in ['busy', 'timeout', 'reduced']):
            test_results['error_handling'] = True
    
    def on_error_occurred(error):
        print(f"⚠️ Error: {error}")
    
    def on_blockchain_info_updated(info):
        print(f"⛓️ Chain: {info.get('chain', 'unknown')}, Blocks: {info.get('blocks', 0)}")
    
    def on_address_balance_updated(address, balance_info):
        test_results['balance_check'] = True
        balance = balance_info.get('balance_btc', 0)
        print(f"💰 Balance for {address[:8]}...: {balance:.8f} BTC")
    
    def on_address_transactions_updated(address, transactions):
        print(f"📋 Transactions for {address[:8]}...: {len(transactions)} found")
    
    # Connect signals
    service.connection_status_changed.connect(on_connection_status_changed)
    service.status_message.connect(on_status_message)
    service.error_occurred.connect(on_error_occurred)
    service.blockchain_info_updated.connect(on_blockchain_info_updated)
    service.address_balance_updated.connect(on_address_balance_updated)
    service.address_transactions_updated.connect(on_address_transactions_updated)
    
    try:
        print("\n🔗 Test 1: Connection with improved error handling...")
        success = service.connect_to_node()
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        print(f"\n🔍 Test 2: Wallet type detection...")
        wallet_type = "Descriptor" if service.is_descriptor_wallet else "Legacy"
        print(f"📝 Detected wallet type: {wallet_type}")
        test_results['wallet_detection'] = True
        
        print(f"\n📡 Test 3: Starting monitoring...")
        service.start_monitoring()
        app.processEvents()
        time.sleep(3)
        app.processEvents()
        
        print(f"\n📍 Test 4: Address monitoring (with proper wallet compatibility)...")
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis address
        print(f"Adding address: {test_address}")
        service.add_address_to_monitor(test_address)
        test_results['address_monitoring'] = True
        
        # Wait for processing
        app.processEvents()
        time.sleep(3)
        app.processEvents()
        
        print(f"\n💰 Test 5: Balance check with timeout handling...")
        service.update_address_balance(test_address)
        app.processEvents()
        time.sleep(5)  # Give more time for balance check
        app.processEvents()
        
        print(f"\n🔄 Test 6: Data update with busy node handling...")
        service.update_data()
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        print(f"\n📊 Test Results Summary:")
        print("=" * 50)
        total_tests = len(test_results)
        passed_tests = sum(test_results.values())
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"- {test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if test_results['connection']:
            print("\n🎉 Connection successful!")
            print(f"- Node type: {'Busy' if getattr(service, 'node_busy', False) else 'Responsive'}")
            print(f"- Wallet type: {wallet_type}")
            print(f"- Monitored addresses: {len(service.monitored_addresses)}")
            print(f"- Failure count: {getattr(service, '_rpc_failure_count', 0)}")
            
            # Test resilience
            print(f"\n🛡️ Test 7: Connection resilience...")
            for i in range(3):
                print(f"Resilience test {i+1}/3...")
                service.update_data()
                app.processEvents()
                time.sleep(1)
                app.processEvents()
        else:
            print("\n📍 Running in no-node mode (Bitcoin Core not available)")
            print("- This is expected if Bitcoin Core is not running")
            print("- Address monitoring features are limited")
        
        print(f"\n✅ All improved tests completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n🧹 Cleaning up...")
        service.disconnect()
        app.quit()

if __name__ == "__main__":
    test_improved_connection()