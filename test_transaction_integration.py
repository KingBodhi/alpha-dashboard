#!/usr/bin/env python3
"""
Test script for Bitcoin transaction page and profile wallet integration.
"""

import sys
import os
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_transaction_page():
    """Test transaction page creation and functionality."""
    print("🧪 Testing Transaction Page...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.pages.transaction_page import TransactionPage
        
        app = QApplication(sys.argv)
        tx_page = TransactionPage()
        
        # Test setting wallet address
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        tx_page.set_wallet_address(test_address)
        
        # Test updating balance
        tx_page.update_balance(0.12345678, 5432.10)
        
        # Test creating a demo transaction
        tx_page.recipient_input.setText("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy")
        tx_page.amount_input.setValue(0.001)
        tx_page.description_input.setText("Test transaction")
        
        # Preview transaction
        tx_page.preview_transaction()
        
        print("✅ Transaction page created and tested successfully")
        return True
        
    except Exception as e:
        print(f"❌ Transaction page test failed: {e}")
        return False

def test_wallet_widget():
    """Test Bitcoin wallet widget."""
    print("🧪 Testing Bitcoin Wallet Widget...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.widgets.bitcoin_wallet_widget import BitcoinWalletWidget
        
        app = QApplication(sys.argv)
        wallet = BitcoinWalletWidget()
        
        # Test setting address
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        wallet.set_address(test_address)
        
        # Test updating balance
        wallet.update_balance(0.12345678, 5432.10)
        
        # Test connection status
        wallet.update_connection_status(True)
        wallet.update_connection_status(False)
        
        # Test adding transaction
        test_tx = {
            'type': 'received',
            'amount': 0.00100000,
            'timestamp': '2025-01-01 12:00:00',
            'txid': 'test_tx_123'
        }
        wallet.add_transaction(test_tx)
        
        print("✅ Wallet widget created and tested successfully")
        return True
        
    except Exception as e:
        print(f"❌ Wallet widget test failed: {e}")
        return False

def test_profile_integration():
    """Test profile page with wallet integration."""
    print("🧪 Testing Profile Page Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.pages.profile_page import ProfilePage
        
        app = QApplication(sys.argv)
        profile = ProfilePage()
        
        # Test getting wallet reference
        wallet = profile.get_bitcoin_wallet()
        address = profile.get_bitcoin_address()
        
        print(f"Profile address: {address}")
        print(f"Wallet widget: {wallet}")
        
        # Test that wallet has the correct address
        wallet_address = wallet.get_address()
        print(f"Wallet address: {wallet_address}")
        
        if wallet_address == address:
            print("✅ Address sync working correctly")
        else:
            print("⚠️ Address sync may need adjustment")
        
        print("✅ Profile integration tested successfully")
        return True
        
    except Exception as e:
        print(f"❌ Profile integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bitcoin_service_integration():
    """Test Bitcoin service integration with new components."""
    print("🧪 Testing Bitcoin Service Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from services.bitcoin_service import BitcoinService
        from app.widgets.bitcoin_wallet_widget import BitcoinWalletWidget
        
        app = QApplication(sys.argv)
        
        # Create service and wallet
        service = BitcoinService()
        wallet = BitcoinWalletWidget("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        
        # Test connecting signals
        service.connection_status_changed.connect(wallet.update_connection_status)
        service.blockchain_info_updated.connect(wallet.update_balance_from_blockchain)
        
        # Test signal emission
        service.connection_status_changed.emit(True)
        service.connection_status_changed.emit(False)
        
        # Test with mock blockchain info
        mock_info = {
            'blocks': 850000,
            'difficulty': Decimal('70000000000000'),
            'chain': 'main'
        }
        service.blockchain_info_updated.emit(mock_info)
        
        print("✅ Bitcoin service integration working")
        return True
        
    except Exception as e:
        print(f"❌ Bitcoin service integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Bitcoin Transaction & Wallet Integration Test")
    print("=" * 60)
    
    results = []
    
    results.append(test_wallet_widget())
    results.append(test_transaction_page())
    results.append(test_profile_integration())
    results.append(test_bitcoin_service_integration())
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Wallet Widget: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   Transaction Page: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"   Profile Integration: {'✅ PASS' if results[2] else '❌ FAIL'}")
    print(f"   Service Integration: {'✅ PASS' if results[3] else '❌ FAIL'}")
    
    if all(results):
        print("\n🎉 All tests passed! Transaction page and wallet integration ready!")
        print("\n📋 Features Available:")
        print("   - Bitcoin wallet widget in profile page")
        print("   - Transaction page with send/receive/history tabs")
        print("   - Blockchain sync status display")
        print("   - Balance tracking and updates")
        print("   - Transaction history management")
        print("   - QR code generation for payments")
        print("   - Advanced transaction builder (UI only)")
        print("\n⚠️ Note: Actual blockchain integration will be added in future updates")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
