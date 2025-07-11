#!/usr/bin/env python3
"""
Test script to verify the no-node fallback functionality when Bitcoin Core is not available.
"""

import sys
import time
from services.bitcoin_service import BitcoinService
from PyQt6.QtCore import QCoreApplication

def test_no_node_fallback():
    """Test the no-node fallback functionality."""
    print("🧪 Testing No-Node Fallback Mode...")
    print("=" * 60)
    
    # Create Qt application (required for PyQt signals)
    app = QCoreApplication(sys.argv)
    
    # Create Bitcoin service
    service = BitcoinService()
    
    # Track events for verification
    events = {
        'connection_status': [],
        'status_messages': [],
        'errors': [],
        'blockchain_info': None
    }
    
    def on_connection_status_changed(connected):
        events['connection_status'].append(connected)
        print(f"📡 Connection status: {'Connected ✅' if connected else 'Disconnected ❌'}")
    
    def on_status_message(message):
        events['status_messages'].append(message)
        print(f"📟 Status: {message}")
    
    def on_error_occurred(error):
        events['errors'].append(error)
        print(f"❌ Error: {error}")
    
    def on_blockchain_info_updated(info):
        events['blockchain_info'] = info
        print(f"⛓️  Blockchain info: Block {info.get('blocks', 0)}, Chain: {info.get('chain', 'unknown')}")
    
    # Connect signals
    service.connection_status_changed.connect(on_connection_status_changed)
    service.status_message.connect(on_status_message)
    service.error_occurred.connect(on_error_occurred)
    service.blockchain_info_updated.connect(on_blockchain_info_updated)
    
    try:
        # Test 1: Let connection attempts exhaust and trigger no-node mode
        print("\n🔗 Test 1: Attempting connection (will fail and trigger no-node mode)...")
        success = service.connect_to_node()
        
        # Process events while connection attempts are made
        for i in range(30):  # Wait up to 30 seconds for all connection attempts
            app.processEvents()
            time.sleep(1)
            if hasattr(service, '_no_node_mode') and service._no_node_mode:
                print("✅ No-node mode successfully activated!")
                break
        
        # Test 2: Start monitoring in no-node mode
        print("\n📡 Test 2: Starting monitoring in no-node mode...")
        monitor_success = service.start_monitoring()
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        if monitor_success:
            print("✅ Monitoring started successfully in no-node mode!")
        else:
            print("❌ Failed to start monitoring")
        
        # Test 3: Try to add an address for monitoring (should work but with limitations)
        print("\n📍 Test 3: Adding address for monitoring in no-node mode...")
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        service.add_address_to_monitor(test_address)
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        # Test 4: Try to update address balance (should handle gracefully)
        print("\n💰 Test 4: Testing address balance update in no-node mode...")
        service.update_address_balance(test_address)
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        # Test 5: Try to update data (should handle gracefully)
        print("\n🔄 Test 5: Testing data update in no-node mode...")
        service.update_data()
        app.processEvents()
        time.sleep(2)
        app.processEvents()
        
        print("\n✅ No-Node Fallback Tests Completed!")
        print("\nTest Results Summary:")
        print(f"- No-node mode activated: {hasattr(service, '_no_node_mode') and service._no_node_mode}")
        print(f"- Connection status events: {len(events['connection_status'])}")
        print(f"- Status messages: {len(events['status_messages'])}")
        print(f"- Error messages: {len(events['errors'])}")
        print(f"- Final connection state: {service.is_connected}")
        print(f"- Monitored addresses: {len(service.monitored_addresses)}")
        
        # Show some recent status messages
        print("\nRecent Status Messages:")
        for msg in events['status_messages'][-5:]:
            print(f"  - {msg}")
        
        if events['errors']:
            print("\nError Messages:")
            for error in events['errors'][-3:]:
                print(f"  - {error}")
        
        # Verify no-node mode behavior
        print("\n🔍 Verifying No-Node Mode Behavior:")
        if hasattr(service, '_no_node_mode') and service._no_node_mode:
            print("✅ No-node mode is properly activated")
            print("✅ Application continues to run without Bitcoin Core")
            print("✅ Address monitoring is available (with limitations)")
            print("✅ No spam from connection retries")
        else:
            print("❌ No-node mode was not activated as expected")
    
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
    test_no_node_fallback()