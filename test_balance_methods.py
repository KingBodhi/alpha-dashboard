#!/usr/bin/env python3
"""
Balance Check Performance Comparison
Tests listunspent vs scantxoutset performance for Bitcoin address balance checking.
"""

import sys
import time
import os
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bitcoinrpc.authproxy import AuthServiceProxy
    from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project directory")
    sys.exit(1)

def test_balance_methods():
    """Compare performance of listunspent vs scantxoutset."""
    print("⚡ Balance Check Performance Comparison")
    print("=" * 50)
    
    try:
        # Connect to Bitcoin Core
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=60)
        
        # Test with a sample address (replace with your own address for better results)
        test_address = input("Enter a Bitcoin address to test (or press Enter for default): ").strip()
        if not test_address:
            test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"  # Example address
        
        print(f"🎯 Testing address: {test_address[:20]}...")
        print()
        
        # Method 1: listunspent (fast for wallet addresses)
        print("🚀 Method 1: listunspent (wallet-based)")
        print("   This method checks UTXOs in the wallet only")
        
        try:
            start_time = time.time()
            unspent_outputs = rpc.listunspent(0, 999999999)  # Include unconfirmed
            listunspent_time = time.time() - start_time
            
            # Filter for our test address
            address_utxos = [utxo for utxo in unspent_outputs if utxo.get('address') == test_address]
            balance_listunspent = sum(Decimal(str(utxo.get('amount', 0))) for utxo in address_utxos)
            
            print(f"   ⏱️ Time: {listunspent_time:.3f}s")
            print(f"   💰 Balance: {balance_listunspent:.8f} BTC")
            print(f"   📦 UTXOs: {len(address_utxos)}")
            print(f"   📊 Total UTXOs checked: {len(unspent_outputs)}")
            
            if listunspent_time > 1:
                status_listunspent = "🐌 SLOW"
            elif listunspent_time > 0.1:
                status_listunspent = "⚠️ Moderate"
            else:
                status_listunspent = "✅ FAST"
            print(f"   🎯 Performance: {status_listunspent}")
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            listunspent_time = float('inf')
            balance_listunspent = Decimal('0')
            status_listunspent = "❌ ERROR"
        
        print()
        
        # Method 2: scantxoutset (slow, scans entire UTXO set)
        print("🔍 Method 2: scantxoutset (full blockchain scan)")
        print("   This method scans the entire UTXO set")
        print("   ⚠️ WARNING: This may take 30-60+ seconds!")
        
        proceed = input("   Continue with scantxoutset test? (y/N): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("   Skipping scantxoutset test")
            scantxoutset_time = float('inf')
            balance_scantxoutset = Decimal('0')
            status_scantxoutset = "⏭️ SKIPPED"
        else:
            try:
                start_time = time.time()
                scan_result = rpc.scantxoutset("start", [f"addr({test_address})"])
                scantxoutset_time = time.time() - start_time
                
                if scan_result:
                    balance_scantxoutset = Decimal(str(scan_result.get('total_amount', 0)))
                    utxo_count = len(scan_result.get('unspents', []))
                else:
                    balance_scantxoutset = Decimal('0')
                    utxo_count = 0
                
                print(f"   ⏱️ Time: {scantxoutset_time:.1f}s")
                print(f"   💰 Balance: {balance_scantxoutset:.8f} BTC")
                print(f"   📦 UTXOs: {utxo_count}")
                
                if scantxoutset_time > 30:
                    status_scantxoutset = "🐌 VERY SLOW"
                elif scantxoutset_time > 10:
                    status_scantxoutset = "⚠️ SLOW"
                elif scantxoutset_time > 5:
                    status_scantxoutset = "🟡 Moderate"
                else:
                    status_scantxoutset = "✅ FAST"
                print(f"   🎯 Performance: {status_scantxoutset}")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                scantxoutset_time = float('inf')
                balance_scantxoutset = Decimal('0')
                status_scantxoutset = "❌ ERROR"
        
        print()
        
        # Performance Comparison
        print("📊 Performance Comparison")
        print("=" * 30)
        print(f"listunspent:   {listunspent_time:.3f}s {status_listunspent}")
        print(f"scantxoutset:  {scantxoutset_time:.1f}s {status_scantxoutset}")
        
        if listunspent_time != float('inf') and scantxoutset_time != float('inf'):
            speedup = scantxoutset_time / listunspent_time if listunspent_time > 0 else float('inf')
            print(f"Speedup:       {speedup:.1f}x faster with listunspent")
            
            if speedup > 100:
                recommendation = "🚀 EXCELLENT - Use listunspent for best performance"
            elif speedup > 10:
                recommendation = "✅ GOOD - listunspent provides significant improvement"
            elif speedup > 2:
                recommendation = "⚠️ MODERATE - Some improvement with listunspent"
            else:
                recommendation = "🤔 SIMILAR - Both methods have similar performance"
            
            print(f"Recommendation: {recommendation}")
        
        # Balance Comparison
        print()
        print("💰 Balance Comparison")
        print("=" * 20)
        print(f"listunspent:   {balance_listunspent:.8f} BTC")
        print(f"scantxoutset:  {balance_scantxoutset:.8f} BTC")
        
        if balance_listunspent != balance_scantxoutset and balance_scantxoutset != Decimal('0'):
            print("⚠️ DIFFERENCE DETECTED!")
            print("   This suggests the address may not be in the wallet")
            print("   Dashboard will use scantxoutset as fallback for such addresses")
        elif balance_listunspent == balance_scantxoutset and balance_listunspent > 0:
            print("✅ BALANCES MATCH - Address is in wallet, listunspent is preferred")
        elif balance_listunspent == 0 and balance_scantxoutset == 0:
            print("ℹ️ NO BALANCE - Both methods agree the address has no funds")
        
        print()
        print("💡 Dashboard Optimization Impact:")
        print("   • Fast addresses (in wallet): Use listunspent - very responsive")
        print("   • Slow addresses (not in wallet): Use scantxoutset - throttled updates")
        print("   • Mixed addresses: Automatic fallback for best performance")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Please ensure Bitcoin Core is running and accessible")

if __name__ == "__main__":
    test_balance_methods()
