#!/usr/bin/env python3
"""
Test script to verify optimized balance checking for slow scantxoutset scenarios.
"""

import time
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.bitcoin_service import BitcoinService
from PyQt6.QtCore import QCoreApplication, QTimer

def test_slow_address_handling():
    """Test that slow addresses are properly tracked and throttled."""
    print("🧪 Testing optimized balance checking for slow addresses...")
    
    app = QCoreApplication(sys.argv)
    
    # Create Bitcoin service
    service = BitcoinService()
    
    # Test address (replace with your actual address)
    test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"  # Example bech32 address
    
    def run_test():
        print(f"\n📊 Testing balance check for {test_address[:8]}...")
        
        # First call - should trigger slow scan detection
        print("🔄 First balance check (will be slow)...")
        start_time = time.time()
        service.update_address_balance(test_address)
        elapsed = time.time() - start_time
        print(f"⏱️ First check completed in {elapsed:.1f}s")
        
        # Check if address was marked as slow
        slow_addresses = getattr(service, '_slow_scan_addresses', {})
        if test_address in slow_addresses:
            print(f"✅ Address correctly marked as slow")
            print(f"📅 Slow address timestamp: {slow_addresses[test_address]}")
        else:
            print(f"❌ Address was NOT marked as slow (this may be expected if scan was fast)")
        
        # Test the monitoring behavior
        print(f"\n🔄 Testing address monitoring behavior...")
        service.monitored_addresses.add(test_address)
        
        # First monitoring call
        print("📍 First monitoring call...")
        service.update_all_monitored_addresses()
        
        # Second monitoring call (should be skipped if address is slow)
        print("📍 Second monitoring call (should skip slow address)...")
        service.update_all_monitored_addresses()
        
        # Third monitoring call
        print("📍 Third monitoring call (should still skip slow address)...")
        service.update_all_monitored_addresses()
        
        print(f"\n✅ Test completed! Check logs above for slow address behavior.")
        app.quit()
    
    # Run the test after a short delay
    QTimer.singleShot(1000, run_test)
    
    # Start the event loop
    app.exec_()

if __name__ == "__main__":
    test_slow_address_handling()
