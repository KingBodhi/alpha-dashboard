#!/usr/bin/env python3
"""
Advanced diagnostic tool to understand what Bitcoin Core is actually doing
when it appears "busy" despite low system resource usage.
"""

import sys
import time
import threading
from datetime import datetime
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG

def diagnose_bitcoin_core_activity():
    """Diagnose what Bitcoin Core is actually busy doing."""
    print("🔍 Diagnosing Bitcoin Core Activity")
    print("=" * 80)
    
    try:
        # Connect with longer timeout
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=60)  # Longer timeout
        
        print("📊 Basic Node Status...")
        try:
            start_time = time.time()
            info = rpc.getblockchaininfo()
            response_time = time.time() - start_time
            
            print(f"   ✅ getblockchaininfo: {response_time:.2f}s")
            print(f"   Chain: {info.get('chain')}")
            print(f"   Blocks: {info.get('blocks'):,}")
            print(f"   Headers: {info.get('headers'):,}")
            print(f"   Sync progress: {info.get('verificationprogress', 0) * 100:.2f}%")
            print(f"   Chain work: {info.get('chainwork', 'unknown')}")
            print(f"   Difficulty: {info.get('difficulty', 0):,.0f}")
            
            # Check if still syncing
            if info.get('verificationprogress', 1) < 0.9999:
                print(f"   ⚠️ Still syncing! ({(1-info.get('verificationprogress', 1))*100:.4f}% remaining)")
            
        except Exception as e:
            print(f"   ❌ Basic info failed: {e}")
            return
        print()
        
        print("🌐 Network Activity...")
        try:
            start_time = time.time()
            net_info = rpc.getnetworkinfo()
            response_time = time.time() - start_time
            
            print(f"   ✅ getnetworkinfo: {response_time:.2f}s")
            print(f"   Version: {net_info.get('version', 'unknown')}")
            print(f"   Connections: {net_info.get('connections', 0)}")
            print(f"   Local services: {hex(net_info.get('localservices', 0))}")
            
            # Get peer info to see network activity
            start_time = time.time()
            peers = rpc.getpeerinfo()
            response_time = time.time() - start_time
            
            print(f"   ✅ getpeerinfo: {response_time:.2f}s ({len(peers)} peers)")
            
            # Analyze peer activity
            recent_blocks = sum(1 for p in peers if p.get('last_block', 0) > info.get('blocks', 0) - 10)
            downloading = sum(1 for p in peers if p.get('synced_blocks', -1) < info.get('blocks', 0))
            
            print(f"   Recent block activity: {recent_blocks} peers")
            print(f"   Downloading from: {downloading} peers")
            
        except Exception as e:
            print(f"   ❌ Network info failed: {e}")
        print()
        
        print("💾 Memory Pool Status...")
        try:
            start_time = time.time()
            mempool = rpc.getmempoolinfo()
            response_time = time.time() - start_time
            
            print(f"   ✅ getmempoolinfo: {response_time:.2f}s")
            print(f"   Transactions: {mempool.get('size', 0):,}")
            print(f"   Memory usage: {mempool.get('usage', 0) / 1024 / 1024:.1f} MB")
            print(f"   Max memory: {mempool.get('maxmempool', 0) / 1024 / 1024:.1f} MB")
            print(f"   Memory percent: {mempool.get('usage', 0) / mempool.get('maxmempool', 1) * 100:.1f}%")
            
            if mempool.get('size', 0) > 50000:
                print(f"   ⚠️ Large mempool! This can cause slowdowns.")
                
        except Exception as e:
            print(f"   ❌ Mempool info failed: {e}")
        print()
        
        print("⛏️ Mining & Processing...")
        try:
            start_time = time.time()
            mining_info = rpc.getmininginfo()
            response_time = time.time() - start_time
            
            print(f"   ✅ getmininginfo: {response_time:.2f}s")
            print(f"   Network hashrate: {mining_info.get('networkhashps', 0) / 1e18:.2f} EH/s")
            print(f"   Difficulty: {mining_info.get('difficulty', 0):,.0f}")
            print(f"   Pool transactions: {mining_info.get('pooledtx', 0):,}")
            
        except Exception as e:
            print(f"   ❌ Mining info failed: {e}")
        print()
        
        print("🔧 RPC Performance Test...")
        test_calls = [
            ("getbestblockhash", lambda: rpc.getbestblockhash()),
            ("getblockcount", lambda: rpc.getblockcount()),
            ("getdifficulty", lambda: rpc.getdifficulty()),
            ("getconnectioncount", lambda: rpc.getconnectioncount()),
        ]
        
        for call_name, call_func in test_calls:
            try:
                start_time = time.time()
                result = call_func()
                response_time = time.time() - start_time
                print(f"   ✅ {call_name}: {response_time:.3f}s")
            except Exception as e:
                print(f"   ❌ {call_name}: {e}")
        print()
        
        print("🔍 Heavy Operation Test...")
        heavy_tests = [
            ("listunspent (limited)", lambda: rpc.listunspent(1, 999999999)[:10]),
            ("listtransactions (10)", lambda: rpc.listtransactions("*", 10)),
            ("getrawmempool (sample)", lambda: list(rpc.getrawmempool())[:10]),
        ]
        
        for test_name, test_func in heavy_tests:
            try:
                start_time = time.time()
                result = test_func()
                response_time = time.time() - start_time
                
                if response_time > 5:
                    print(f"   ⚠️ {test_name}: {response_time:.2f}s (SLOW)")
                elif response_time > 1:
                    print(f"   🟡 {test_name}: {response_time:.2f}s (slow)")
                else:
                    print(f"   ✅ {test_name}: {response_time:.2f}s")
                    
            except Exception as e:
                print(f"   ❌ {test_name}: {e}")
        print()
        
        print("🎯 scantxoutset Test (your main issue)...")
        test_address = "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # Known address with activity
        try:
            print(f"   Testing scantxoutset with address: {test_address[:20]}...")
            start_time = time.time()
            
            # Use a known address that should have UTXOs
            result = rpc.scantxoutset("start", [f"addr({test_address})"])
            response_time = time.time() - start_time
            
            if response_time > 30:
                print(f"   ❌ scantxoutset: {response_time:.1f}s (VERY SLOW - this is your problem!)")
            elif response_time > 10:
                print(f"   ⚠️ scantxoutset: {response_time:.1f}s (slow)")
            else:
                print(f"   ✅ scantxoutset: {response_time:.1f}s")
                
            if result:
                print(f"   Found: {result.get('total_amount', 0):.8f} BTC in {len(result.get('unspents', []))} UTXOs")
                
        except Exception as e:
            print(f"   ❌ scantxoutset test failed: {e}")
        print()
        
        print("📈 Continuous Monitoring (30 seconds)...")
        print("   (This will show if there are periodic heavy operations)")
        
        response_times = []
        for i in range(6):  # 6 tests over 30 seconds
            try:
                start_time = time.time()
                count = rpc.getblockcount()
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                timestamp = datetime.now().strftime("%H:%M:%S")
                if response_time > 2:
                    print(f"   {timestamp}: {response_time:.3f}s ⚠️")
                else:
                    print(f"   {timestamp}: {response_time:.3f}s ✅")
                    
                if i < 5:  # Don't sleep after last iteration
                    time.sleep(5)
                    
            except Exception as e:
                print(f"   {datetime.now().strftime('%H:%M:%S')}: Error - {e}")
        
        avg_time = sum(response_times) / len(response_times) if response_times else 0
        max_time = max(response_times) if response_times else 0
        
        print(f"   Average response: {avg_time:.3f}s")
        print(f"   Maximum response: {max_time:.3f}s")
        print()
        
        print("=" * 80)
        print("🎯 DIAGNOSIS SUMMARY")
        print()
        
        if avg_time > 2:
            print("❌ ISSUE FOUND: Bitcoin Core is consistently slow")
            print("   Possible causes:")
            print("   • Large UTXO database operations")
            print("   • Heavy mempool processing")
            print("   • Disk I/O bottleneck")
            print("   • Many peer connections")
            print("   • Background blockchain maintenance")
        elif max_time > 5:
            print("⚠️ ISSUE FOUND: Bitcoin Core has periodic slowdowns")
            print("   Possible causes:")
            print("   • Periodic database maintenance")
            print("   • Large block processing")
            print("   • Memory garbage collection")
        else:
            print("✅ Bitcoin Core appears responsive")
            print("   Your dashboard issues may be configuration-related")
        
        print()
        print("💡 RECOMMENDATIONS:")
        print("   • Increase RPC timeout to 60-120 seconds")
        print("   • Reduce concurrent RPC calls")
        print("   • Consider using pruned mode if disk space is limited")
        print("   • Monitor during different times of day")
        print("   • Check Bitcoin Core debug.log for errors")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nThis suggests Bitcoin Core is either:")
        print("   • Not running")
        print("   • Completely overloaded")
        print("   • Having network issues")

if __name__ == "__main__":
    diagnose_bitcoin_core_activity()
