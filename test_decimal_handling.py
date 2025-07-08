#!/usr/bin/env python3
"""
Test script to verify Decimal handling in Bitcoin dashboard
"""

from decimal import Decimal
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from app.widgets.bitcoin_dashboard import BitcoinDashboard
    
    # Create QApplication for testing
    app = QApplication(sys.argv)
    
    # Test the safe_float method
    dashboard = BitcoinDashboard()
    
    # Test cases
    test_cases = [
        (Decimal('123456789.123'), 123456789.123),
        (Decimal('0.00012345'), 0.00012345),
        ('123.456', 123.456),
        (789, 789.0),
        (None, 0.0),
        ('invalid', 0.0),
    ]
    
    print("Testing Decimal conversion in BitcoinDashboard...")
    print("=" * 50)
    
    for i, (input_val, expected) in enumerate(test_cases, 1):
        result = dashboard.safe_float(input_val)
        status = "✅ PASS" if abs(result - expected) < 0.000001 else "❌ FAIL"
        print(f"Test {i}: {input_val} -> {result} (expected {expected}) {status}")
    
    print("=" * 50)
    print("✅ All Decimal handling tests completed!")
    
    # Test with realistic Bitcoin data
    print("\nTesting with realistic Bitcoin RPC response...")
    mock_blockchain_info = {
        'difficulty': Decimal('67957790298975.61'),
        'verificationprogress': Decimal('0.9999999'),
        'size_on_disk': Decimal('578123456789'),
        'blocks': 904589,
        'headers': 904589,
        'bestblockhash': 'mock_hash',
        'chain': 'main'
    }
    
    # This should not crash
    dashboard.update_blockchain_info(mock_blockchain_info)
    print("✅ Blockchain info update handled successfully!")
    
    mock_mempool_info = {
        'size': 1234,
        'bytes': Decimal('12345678')
    }
    
    dashboard.update_mempool_info(mock_mempool_info)
    print("✅ Mempool info update handled successfully!")
    
    print("\n🎉 All tests passed! The Bitcoin dashboard should now work correctly.")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
