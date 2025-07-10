#!/usr/bin/env python3
"""
Lightweight Bitcoin address balance checker that works with busy nodes.
Uses minimal RPC calls and aggressive timeouts.
"""

import sys
import time
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG

def check_address_simple(address):
    """Simple, robust address check for busy nodes."""
    print(f"🔍 Checking address: {address}")
    print("Using busy-node-optimized approach...")
    print()
    
    try:
        # Connect with very long timeout
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=120)  # 2 minute timeout
        
        print("📡 Testing connection...")
        try:
            info = rpc.getblockchaininfo()
            print(f"✅ Connected! Blocks: {info.get('blocks'):,}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return
        
        print()
        print("💰 Checking balance (this may take 1-2 minutes on busy nodes)...")
        
        # Method 1: Try scantxoutset with maximum patience
        balance_found = False
        for attempt in range(3):  # 3 attempts
            try:
                print(f"   Attempt {attempt + 1}/3: Running scantxoutset...")
                start_time = time.time()
                
                result = rpc.scantxoutset("start", [f"addr({address})"])
                
                elapsed = time.time() - start_time
                print(f"   ✅ Completed in {elapsed:.1f} seconds")
                
                if result:
                    balance = Decimal(str(result.get('total_amount', 0)))
                    utxo_count = len(result.get('unspents', []))
                    
                    if balance > 0:
                        print(f"   💰 BALANCE FOUND: {balance:.8f} BTC")
                        print(f"   📊 UTXOs: {utxo_count}")
                        
                        # Show recent transactions
                        if result.get('unspents'):
                            print(f"   📋 Recent UTXOs:")
                            for i, utxo in enumerate(result['unspents'][:5]):
                                print(f"      {i+1}. {utxo['txid'][:16]}...:{utxo['vout']} = {utxo['amount']:.8f} BTC")
                        
                        balance_found = True
                        break
                    else:
                        print(f"   📍 Address exists but no current balance")
                        balance_found = True
                        break
                else:
                    print(f"   ⚠️ scantxoutset returned None")
                    
            except Exception as e:
                error_str = str(e).lower()
                if "timeout" in error_str or "request-sent" in error_str:
                    print(f"   ⏰ Timeout on attempt {attempt + 1} ({elapsed:.1f}s)")
                    if attempt < 2:
                        print(f"   ⏳ Waiting 30 seconds before retry...")
                        time.sleep(30)
                    continue
                else:
                    print(f"   ❌ Error: {e}")
                    break
        
        if not balance_found:
            print("❌ Could not check balance - node too busy")
            print("💡 Try again later when node is less busy")
            return
        
        # Method 2: If we found a balance, try to get recent transactions (optional)
        if balance_found and balance > 0:
            print()
            print("📋 Attempting to find recent transactions...")
            
            try:
                # Get just the latest block to find recent activity
                best_hash = rpc.getbestblockhash()
                latest_block = rpc.getblock(best_hash, 2)
                
                found_recent = False
                for tx in latest_block.get('tx', [])[:50]:  # Check first 50 transactions only
                    for vout in tx.get('vout', []):
                        script_pub_key = vout.get('scriptPubKey', {})
                        addresses = script_pub_key.get('addresses', [])
                        if script_pub_key.get('address'):
                            addresses.append(script_pub_key['address'])
                        
                        if address in addresses:
                            print(f"   🔍 Recent activity found: {tx['txid'][:16]}... ({vout.get('value', 0):.8f} BTC)")
                            found_recent = True
                            break
                    
                    if found_recent:
                        break
                
                if not found_recent:
                    print(f"   📍 No activity in latest block (transactions may be older)")
                    
            except Exception as e:
                print(f"   ⚠️ Could not check recent transactions: {e}")
        
        print()
        print("✅ Balance check complete!")
        if balance_found and balance > 0:
            print(f"💰 Your address has {balance:.8f} BTC")
            print("✅ This confirms transactions exist and should show in dashboard")
            print("   once the node becomes less busy")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 simple_balance_check.py <bitcoin_address>")
        sys.exit(1)
    
    address = sys.argv[1]
    check_address_simple(address)
