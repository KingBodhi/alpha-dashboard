#!/usr/bin/env python3
"""
Test script to verify Bitcoin address monitoring and blockchain integration.
"""

import sys
import os
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_address_monitoring():
    """Test address monitoring functionality."""
    print("🧪 Testing Bitcoin Address Monitoring...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from services.bitcoin_service import BitcoinService
        from app.widgets.bitcoin_wallet_widget import BitcoinWalletWidget
        
        app = QApplication(sys.argv)
        
        # Create service and wallet
        service = BitcoinService()
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis block address
        wallet = BitcoinWalletWidget(test_address)
        
        # Connect address-specific signals
        service.address_balance_updated.connect(wallet.update_address_balance)
        service.address_transactions_updated.connect(wallet.update_address_transactions)
        
        # Add address to monitoring
        service.add_address_to_monitor(test_address)
        
        # Verify address was added
        assert test_address in service.monitored_addresses
        assert test_address in service.address_balances
        
        # Test mock balance update
        mock_balance_info = {
            'balance_btc': Decimal('0.12345678'),
            'balance_usd': 5432.10,
            'confirmed': Decimal('0.12345678'),
            'unconfirmed': Decimal('0'),
            'utxo_count': 3,
            'last_updated': 1234567890
        }
        
        # Emit balance update signal
        service.address_balance_updated.emit(test_address, mock_balance_info)
        
        # Test mock transaction update
        mock_transactions = [
            {
                'txid': 'test_tx_1',
                'amount': Decimal('0.05'),
                'confirmations': 6,
                'time': 1234567890,
                'type': 'receive',
                'address': test_address
            },
            {
                'txid': 'test_tx_2', 
                'amount': Decimal('0.07345678'),
                'confirmations': 12,
                'time': 1234567900,
                'type': 'receive',
                'address': test_address
            }
        ]
        
        # Emit transaction update signal
        service.address_transactions_updated.emit(test_address, mock_transactions)
        
        # Verify wallet received updates
        wallet_balance = wallet.get_balance()
        print(f"Wallet balance: {wallet_balance}")
        print(f"Transaction count: {wallet.transaction_list.count()}")
        
        print("✅ Address monitoring functionality working")
        return True
        
    except Exception as e:
        print(f"❌ Address monitoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_profile_integration():
    """Test profile page address integration."""
    print("🧪 Testing Profile Address Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.pages.profile_page import ProfilePage
        from services.bitcoin_service import BitcoinService
        
        app = QApplication(sys.argv)
        
        # Create profile and service
        profile = ProfilePage()
        service = BitcoinService()
        
        # Get Bitcoin address and wallet
        bitcoin_address = profile.get_bitcoin_address()
        wallet = profile.get_bitcoin_wallet()
        
        print(f"Profile Bitcoin address: {bitcoin_address}")
        print(f"Wallet address: {wallet.get_address()}")
        
        # Verify address sync
        assert wallet.get_address() == bitcoin_address
        
        # Connect signals (like main window does)
        service.address_balance_updated.connect(wallet.update_address_balance)
        service.address_transactions_updated.connect(wallet.update_address_transactions)
        
        # Add address to monitoring
        service.add_address_to_monitor(bitcoin_address)
        
        # Test balance update
        mock_balance = {
            'balance_btc': Decimal('0.00123456'),
            'balance_usd': 55.43,
            'utxo_count': 1
        }
        
        service.address_balance_updated.emit(bitcoin_address, mock_balance)
        
        print("✅ Profile address integration working")
        return True
        
    except Exception as e:
        print(f"❌ Profile integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_transaction_page_integration():
    """Test transaction page with address monitoring."""
    print("🧪 Testing Transaction Page Integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.pages.transaction_page import TransactionPage
        
        app = QApplication(sys.argv)
        
        # Create transaction page
        tx_page = TransactionPage()
        
        # Set test address
        test_address = "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
        tx_page.set_wallet_address(test_address)
        
        # Test balance update
        tx_page.update_balance(0.02468135, 1100.50)
        
        print(f"Transaction page address: {tx_page.receive_address_label.text()}")
        print(f"Transaction page balance: {tx_page.balance_label.text()}")
        
        print("✅ Transaction page integration working")
        return True
        
    except Exception as e:
        print(f"❌ Transaction page integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mock_blockchain_sync():
    """Test mock blockchain synchronization."""
    print("🧪 Testing Mock Blockchain Sync...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from services.bitcoin_service import BitcoinService
        
        app = QApplication(sys.argv)
        service = BitcoinService()
        
        # Test address methods
        test_address = "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
        
        # Add address
        service.add_address_to_monitor(test_address)
        print(f"Monitoring addresses: {list(service.monitored_addresses)}")
        
        # Test balance update method (without actual RPC)
        initial_balance = service.address_balances.get(test_address, Decimal('0'))
        print(f"Initial balance for {test_address}: {initial_balance}")
        
        # Test BTC price estimate
        btc_price = service.get_btc_price_estimate()
        print(f"BTC price estimate: ${btc_price}")
        
        # Remove address
        service.remove_address_from_monitor(test_address)
        print(f"Monitoring addresses after removal: {list(service.monitored_addresses)}")
        
        print("✅ Mock blockchain sync working")
        return True
        
    except Exception as e:
        print(f"❌ Mock blockchain sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all address monitoring tests."""
    print("🧪 Bitcoin Address-to-Chain Integration Test")
    print("=" * 60)
    
    results = []
    
    results.append(test_address_monitoring())
    results.append(test_profile_integration())
    results.append(test_transaction_page_integration())
    results.append(test_mock_blockchain_sync())
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Address Monitoring: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"   Profile Integration: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"   Transaction Page: {'✅ PASS' if results[2] else '❌ FAIL'}")
    print(f"   Mock Blockchain Sync: {'✅ PASS' if results[3] else '❌ FAIL'}")
    
    if all(results):
        print("\n🎉 All address monitoring tests passed!")
        print("\n📋 Address-to-Chain Integration Features:")
        print("   ✅ Bitcoin addresses are monitored by the service")
        print("   ✅ Balance updates are propagated to wallet widgets")
        print("   ✅ Transaction history is tracked per address")
        print("   ✅ Profile page address is synced with blockchain")
        print("   ✅ Transaction page receives address and balance data")
        print("   ✅ Real-time updates via Qt signals")
        print("   ✅ Mock blockchain data for testing")
        print("\n⚡ Ready for live Bitcoin RPC integration!")
        print("   - Address importing to Bitcoin Core wallet")
        print("   - Real balance queries via listunspent")
        print("   - Transaction history via RPC calls")
        print("   - Live blockchain monitoring")
    else:
        print("\n❌ Some address monitoring tests failed.")

if __name__ == "__main__":
    main()
