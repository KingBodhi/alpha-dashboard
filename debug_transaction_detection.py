#!/usr/bin/env python3
"""
Debug script to test transaction detection for a specific Bitcoin address.
This script helps diagnose why transactions might not be showing up in the dashboard.
"""

import sys
import time
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG

def test_address_detection(address):
    """Test various methods to detect transactions for an address."""
    print(f"🔍 Testing transaction detection for address: {address}")
    print("=" * 80)
    
    try:
        # Connect to Bitcoin Core
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=30)
        
        # Test connection
        info = rpc.getblockchaininfo()
        print(f"✅ Connected to Bitcoin Core")
        print(f"   Chain: {info.get('chain')}")
        print(f"   Blocks: {info.get('blocks')}")
        print(f"   Sync progress: {info.get('verificationprogress', 0) * 100:.1f}%")
        print()
        
        # Test 1: Check if address is valid
        print("1️⃣ Testing address validity...")
        try:
            addr_info = rpc.validateaddress(address)
            if addr_info.get('isvalid'):
                print(f"   ✅ Address is valid")
                print(f"   Type: {addr_info.get('type', 'unknown')}")
                print(f"   Script type: {addr_info.get('scripttype', 'unknown')}")
            else:
                print(f"   ❌ Address is invalid!")
                return False
        except Exception as e:
            print(f"   ⚠️ Could not validate address: {e}")
        print()
        
        # Test 2: Try to get address info (if in wallet)
        print("2️⃣ Testing wallet address info...")
        try:
            addr_info = rpc.getaddressinfo(address)
            print(f"   ✅ Address info available")
            print(f"   Is mine: {addr_info.get('ismine', False)}")
            print(f"   Is watchonly: {addr_info.get('iswatchonly', False)}")
            print(f"   Label: {addr_info.get('label', 'none')}")
            if addr_info.get('hdkeypath'):
                print(f"   HD path: {addr_info.get('hdkeypath')}")
        except Exception as e:
            print(f"   ⚠️ Address not in wallet or error: {e}")
        print()
        
        # Test 3: Try importing address (for legacy wallets)
        print("3️⃣ Testing address import...")
        try:
            # Try importing without rescan first
            rpc.importaddress(address, f"debug_{address[:8]}", False)
            print(f"   ✅ Address imported successfully (no rescan)")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   ✅ Address already imported")
            elif "descriptor wallet" in str(e).lower():
                print(f"   ⚠️ Descriptor wallet - import not needed")
            else:
                print(f"   ❌ Import failed: {e}")
                # Try with rescan for legacy wallets
                try:
                    rpc.importaddress(address, f"debug_{address[:8]}", True)
                    print(f"   ✅ Address imported with rescan")
                except Exception as e2:
                    print(f"   ❌ Import with rescan failed: {e2}")
        print()
        
        # Test 4: Balance detection methods
        print("4️⃣ Testing balance detection...")
        
        # Method A: scantxoutset
        try:
            scan_result = rpc.scantxoutset("start", [f"addr({address})"])
            if scan_result:
                balance = Decimal(str(scan_result.get('total_amount', 0)))
                utxo_count = len(scan_result.get('unspents', []))
                print(f"   ✅ scantxoutset: {balance:.8f} BTC ({utxo_count} UTXOs)")
                if scan_result.get('unspents'):
                    print(f"      Recent UTXOs:")
                    for i, utxo in enumerate(scan_result['unspents'][:3]):
                        print(f"        {i+1}. {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['amount']:.8f} BTC")
            else:
                print(f"   ⚠️ scantxoutset returned None (node busy or no UTXOs)")
        except Exception as e:
            print(f"   ❌ scantxoutset failed: {e}")
        
        # Method B: listunspent
        try:
            unspent = rpc.listunspent(0, 9999999, [address])
            if unspent:
                balance = sum(Decimal(str(utxo['amount'])) for utxo in unspent)
                print(f"   ✅ listunspent: {balance:.8f} BTC ({len(unspent)} UTXOs)")
            else:
                print(f"   ⚠️ listunspent: No UTXOs found")
        except Exception as e:
            print(f"   ❌ listunspent failed: {e}")
        
        # Method C: listreceivedbyaddress
        try:
            received = rpc.listreceivedbyaddress(0, True, True, address)
            if received:
                for entry in received:
                    if entry.get('address') == address:
                        print(f"   ✅ listreceivedbyaddress: {entry.get('amount', 0):.8f} BTC ({entry.get('txids', [])})")
                        break
            else:
                print(f"   ⚠️ listreceivedbyaddress: No entries found")
        except Exception as e:
            print(f"   ❌ listreceivedbyaddress failed: {e}")
        print()
        
        # Test 5: Transaction detection methods
        print("5️⃣ Testing transaction detection...")
        
        # Method A: Wallet transactions
        try:
            wallet_txs = rpc.listtransactions("*", 1000, 0, True)
            matching_txs = []
            for tx in wallet_txs:
                if tx.get('address') == address:
                    matching_txs.append(tx)
                elif tx.get('details'):
                    for detail in tx['details']:
                        if detail.get('address') == address:
                            matching_txs.append(tx)
                            break
            
            print(f"   ✅ listtransactions: {len(matching_txs)} transactions found")
            for i, tx in enumerate(matching_txs[:3]):
                print(f"      {i+1}. {tx['txid'][:16]}... ({tx.get('category', 'unknown')}) {tx.get('amount', 0):.8f} BTC")
                
        except Exception as e:
            print(f"   ❌ listtransactions failed: {e}")
        
        # Method B: Block scanning (limited)
        try:
            print(f"   🔍 Scanning recent blocks...")
            best_hash = rpc.getbestblockhash()
            current_hash = best_hash
            found_txs = []
            
            for i in range(10):  # Scan last 10 blocks
                if not current_hash:
                    break
                    
                block = rpc.getblock(current_hash, 2)
                for tx in block.get('tx', []):
                    # Check outputs
                    for vout in tx.get('vout', []):
                        script_pub_key = vout.get('scriptPubKey', {})
                        addresses = script_pub_key.get('addresses', [])
                        if script_pub_key.get('address'):
                            addresses.append(script_pub_key['address'])
                        
                        if address in addresses:
                            found_txs.append((tx['txid'], vout.get('value', 0), 'receive'))
                
                current_hash = block.get('previousblockhash')
            
            print(f"   ✅ Block scan (10 blocks): {len(found_txs)} transactions found")
            for i, (txid, amount, tx_type) in enumerate(found_txs[:3]):
                print(f"      {i+1}. {txid[:16]}... ({tx_type}) {amount:.8f} BTC")
                
        except Exception as e:
            print(f"   ❌ Block scanning failed: {e}")
        print()
        
        # Test 6: Advanced methods
        print("6️⃣ Testing advanced detection...")
        
        # Try searchrawtransactions if available
        try:
            search_result = rpc.searchrawtransactions(address, True, 0, 10)
            print(f"   ✅ searchrawtransactions: {len(search_result)} transactions found")
        except Exception as e:
            print(f"   ⚠️ searchrawtransactions not available: {e}")
        
        print()
        print("=" * 80)
        print("🔍 Diagnosis complete!")
        print()
        print("💡 Tips for troubleshooting:")
        print("   • If no transactions found but balance exists, try importing with rescan")
        print("   • For descriptor wallets, use scantxoutset instead of import")
        print("   • Check if Bitcoin Core is fully synced")
        print("   • Verify the address format matches your wallet type")
        print("   • Consider increasing block scan range for older transactions")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Check that:")
        print("   • Bitcoin Core is running")
        print("   • RPC credentials are correct")
        print("   • RPC server is enabled in bitcoin.conf")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_transaction_detection.py <bitcoin_address>")
        print("Example: python debug_transaction_detection.py bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
        sys.exit(1)
    
    address = sys.argv[1]
    test_address_detection(address)
