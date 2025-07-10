#!/usr/bin/env python3
"""
Wallet Fund Detection Diagnostic
This tool investigates why the dashboard isn't detecting existing wallet funds.
"""

import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_wallet_fund_detection():
    """Diagnose why dashboard isn't detecting existing wallet funds."""
    print("🔍 Wallet Fund Detection Diagnostic")
    print("=" * 60)
    
    try:
        from bitcoinrpc.authproxy import AuthServiceProxy
        from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
        
        # Connect to Bitcoin Core
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=120)
        
        print("📡 Connected to Bitcoin Core")
        
        # 1. Check wallet status
        print("\n💼 Wallet Status Check...")
        try:
            wallet_info = rpc.getwalletinfo()
            print(f"   Wallet name: {wallet_info.get('walletname', 'default')}")
            print(f"   Wallet version: {wallet_info.get('walletversion', 'unknown')}")
            print(f"   Balance: {wallet_info.get('balance', 0):.8f} BTC")
            print(f"   Unconfirmed balance: {wallet_info.get('unconfirmed_balance', 0):.8f} BTC")
            print(f"   Immature balance: {wallet_info.get('immature_balance', 0):.8f} BTC")
            print(f"   Keypoolsize: {wallet_info.get('keypoolsize', 0)}")
            print(f"   Descriptor wallet: {wallet_info.get('descriptors', False)}")
            
            total_balance = wallet_info.get('balance', 0) + wallet_info.get('unconfirmed_balance', 0)
            if total_balance > 0:
                print(f"   ✅ WALLET HAS FUNDS: {total_balance:.8f} BTC")
            else:
                print(f"   ❌ No funds detected in wallet")
                
        except Exception as e:
            print(f"   ❌ Wallet info failed: {e}")
        
        # 2. List all wallet addresses
        print(f"\n📋 Wallet Addresses...")
        try:
            # Get all addresses in the wallet
            addresses = rpc.getaddressesbylabel("")
            print(f"   Total addresses in wallet: {len(addresses)}")
            
            if len(addresses) > 0:
                print(f"   Sample addresses:")
                for i, addr in enumerate(list(addresses.keys())[:5]):
                    addr_info = rpc.getaddressinfo(addr)
                    addr_type = "Unknown"
                    if addr.startswith('1'):
                        addr_type = "Legacy"
                    elif addr.startswith('3'):
                        addr_type = "P2SH"
                    elif addr.startswith('bc1'):
                        addr_type = "Native Segwit"
                    
                    print(f"     {i+1}. {addr} ({addr_type})")
                    print(f"        Mine: {addr_info.get('ismine', False)}")
                    print(f"        Watchonly: {addr_info.get('iswatchonly', False)}")
            
        except Exception as e:
            print(f"   ❌ Address listing failed: {e}")
        
        # 3. Check listunspent (all UTXOs in wallet)
        print(f"\n💰 UTXO Analysis...")
        try:
            utxos = rpc.listunspent(0, 999999999)
            print(f"   Total UTXOs in wallet: {len(utxos)}")
            
            if len(utxos) > 0:
                total_value = sum(utxo.get('amount', 0) for utxo in utxos)
                print(f"   ✅ TOTAL UTXO VALUE: {total_value:.8f} BTC")
                
                # Group by address type
                address_types = {}
                for utxo in utxos:
                    addr = utxo.get('address', '')
                    if addr.startswith('1'):
                        addr_type = "Legacy"
                    elif addr.startswith('3'):
                        addr_type = "P2SH"
                    elif addr.startswith('bc1'):
                        addr_type = "Native Segwit"
                    else:
                        addr_type = "Unknown"
                    
                    if addr_type not in address_types:
                        address_types[addr_type] = {'count': 0, 'value': 0}
                    address_types[addr_type]['count'] += 1
                    address_types[addr_type]['value'] += utxo.get('amount', 0)
                
                print(f"   UTXO breakdown by address type:")
                for addr_type, data in address_types.items():
                    print(f"     {addr_type}: {data['count']} UTXOs, {data['value']:.8f} BTC")
                
                # Show sample UTXOs
                print(f"   Sample UTXOs:")
                for i, utxo in enumerate(utxos[:3]):
                    print(f"     {i+1}. {utxo.get('address', '')}: {utxo.get('amount', 0):.8f} BTC")
                    print(f"        Confirmations: {utxo.get('confirmations', 0)}")
                    print(f"        Spendable: {utxo.get('spendable', False)}")
            else:
                print(f"   ❌ No UTXOs found in wallet")
                
        except Exception as e:
            print(f"   ❌ UTXO listing failed: {e}")
        
        # 4. Test dashboard's address checking method
        print(f"\n🎯 Dashboard Address Test...")
        
        # Get the address the dashboard would use
        try:
            # Check if we can find dashboard's profile
            profile_addresses = []
            
            # Try to get addresses from wallet that match dashboard generation pattern
            if len(utxos) > 0:
                # Get unique addresses from UTXOs
                wallet_addresses = list(set(utxo.get('address', '') for utxo in utxos))
                print(f"   Wallet has funds in {len(wallet_addresses)} unique addresses")
                
                # Test each address with dashboard's balance checking method
                for addr in wallet_addresses[:3]:  # Test first 3 addresses
                    print(f"\n   Testing address: {addr[:20]}...")
                    test_dashboard_balance_method(rpc, addr)
            
        except Exception as e:
            print(f"   ❌ Dashboard method test failed: {e}")
        
        # 5. Check what address the dashboard is actually monitoring
        print(f"\n📍 Dashboard Monitoring Check...")
        try:
            from services.bitcoin_service import BitcoinService
            service = BitcoinService()
            
            monitored = getattr(service, 'monitored_addresses', set())
            print(f"   Dashboard monitoring {len(monitored)} addresses:")
            for addr in monitored:
                print(f"     - {addr}")
                
                # Check if this address has funds in the wallet
                addr_utxos = [utxo for utxo in utxos if utxo.get('address') == addr]
                if addr_utxos:
                    addr_balance = sum(utxo.get('amount', 0) for utxo in addr_utxos)
                    print(f"       ✅ HAS FUNDS: {addr_balance:.8f} BTC")
                else:
                    print(f"       ❌ No funds found")
                    
        except Exception as e:
            print(f"   ❌ Dashboard monitoring check failed: {e}")
    
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")

def test_dashboard_balance_method(rpc, address):
    """Test the exact balance checking method the dashboard uses."""
    try:
        # Method 1: listunspent for this specific address
        utxos = rpc.listunspent(0, 999999999)
        addr_utxos = [utxo for utxo in utxos if utxo.get('address') == address]
        listunspent_balance = sum(utxo.get('amount', 0) for utxo in addr_utxos)
        
        print(f"     listunspent result: {listunspent_balance:.8f} BTC ({len(addr_utxos)} UTXOs)")
        
        # Method 2: scantxoutset (what dashboard uses for descriptor wallets)
        start_time = time.time()
        scan_result = rpc.scantxoutset("start", [f"addr({address})"])
        elapsed = time.time() - start_time
        
        if scan_result:
            scan_balance = scan_result.get('total_amount', 0)
            scan_utxos = len(scan_result.get('unspents', []))
            print(f"     scantxoutset result: {scan_balance:.8f} BTC ({scan_utxos} UTXOs) - {elapsed:.1f}s")
            
            # Compare results
            if abs(listunspent_balance - scan_balance) < 0.00000001:
                print(f"     ✅ Methods agree")
            else:
                print(f"     ⚠️ Methods disagree! Difference: {abs(listunspent_balance - scan_balance):.8f}")
        else:
            print(f"     ❌ scantxoutset failed")
            
    except Exception as e:
        print(f"     ❌ Balance method test failed: {e}")

if __name__ == "__main__":
    diagnose_wallet_fund_detection()
