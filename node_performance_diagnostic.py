#!/usr/bin/env python3
"""
Node Performance Diagnostics for Alpha Dashboard
Provides insights into Bitcoin Core RPC performance and slow address tracking.
"""

import time
import json
import sys
import os
from decimal import Decimal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bitcoinrpc.authproxy import AuthServiceProxy
except ImportError:
    print("❌ Error: python-bitcoinrpc not installed")
    print("Please install with: pip install python-bitcoinrpc")
    sys.exit(1)

def test_node_performance():
    """Test various Bitcoin Core RPC operations and provide performance insights."""
    print("🔧 Bitcoin Core Performance Diagnostics")
    print("=" * 50)
    
    # Bitcoin Core connection details
    rpc_user = "bitcoinrpc"
    rpc_password = "your_rpc_password"  # Update this
    rpc_host = "127.0.0.1"
    rpc_port = 8332
    
    try:
        # Connect to Bitcoin Core
        rpc_url = f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}/"
        rpc = AuthServiceProxy(rpc_url, timeout=30)
        
        print(f"🔗 Connecting to Bitcoin Core at {rpc_host}:{rpc_port}...")
        
        # Test 1: Basic connectivity
        print(f"\n📡 Testing basic connectivity...")
        start_time = time.time()
        block_count = rpc.getblockcount()
        basic_response_time = time.time() - start_time
        print(f"✅ Connected successfully")
        print(f"📊 Current block: {block_count:,}")
        print(f"⏱️ Response time: {basic_response_time*1000:.1f}ms")
        
        # Determine performance category
        if basic_response_time < 0.01:  # <10ms
            perf_category = "🚀 Excellent"
        elif basic_response_time < 0.05:  # <50ms
            perf_category = "✅ Good"
        elif basic_response_time < 0.2:  # <200ms
            perf_category = "⚠️ Moderate"
        else:
            perf_category = "🐌 Slow"
        
        print(f"🎯 Node performance: {perf_category}")
        
        # Test 2: Node resource usage
        print(f"\n💾 Testing node resource usage...")
        start_time = time.time()
        mempool_info = rpc.getmempoolinfo()
        memory_response_time = time.time() - start_time
        print(f"📦 Mempool transactions: {mempool_info['size']:,}")
        print(f"💾 Mempool memory usage: {mempool_info['bytes']/1024/1024:.1f} MB")
        print(f"⏱️ Response time: {memory_response_time*1000:.1f}ms")
        
        # Test 3: scantxoutset performance
        print(f"\n🔍 Testing scantxoutset performance...")
        print(f"⚠️ WARNING: This test will take 30-60+ seconds on slow nodes!")
        test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"  # Example address
        
        start_time = time.time()
        try:
            scan_result = rpc.scantxoutset("start", [f"addr({test_address})"])
            scan_response_time = time.time() - start_time
            
            print(f"✅ scantxoutset completed")
            print(f"⏱️ Response time: {scan_response_time:.1f}s")
            
            # Provide recommendations based on scan time
            if scan_response_time < 5:
                scan_category = "🚀 Very Fast"
                recommendation = "Your node can handle frequent balance checks"
            elif scan_response_time < 15:
                scan_category = "✅ Acceptable"
                recommendation = "Dashboard will work well with normal update frequency"
            elif scan_response_time < 30:
                scan_category = "⚠️ Slow"
                recommendation = "Dashboard will automatically reduce update frequency"
            else:
                scan_category = "🐌 Very Slow"
                recommendation = "Dashboard will aggressively throttle slow addresses (15min intervals)"
            
            print(f"🎯 scantxoutset performance: {scan_category}")
            print(f"💡 Recommendation: {recommendation}")
            
        except Exception as e:
            print(f"❌ scantxoutset failed: {e}")
            print(f"💡 Your node may be too busy - dashboard will use fallback methods")
        
        # Test 4: Network status
        print(f"\n🌐 Testing network status...")
        try:
            network_info = rpc.getnetworkinfo()
            peer_info = rpc.getpeerinfo()
            
            print(f"🔗 Network connections: {len(peer_info)}")
            print(f"📡 Network active: {network_info.get('networkactive', 'Unknown')}")
            print(f"🏷️ Version: {network_info.get('subversion', 'Unknown')}")
            
        except Exception as e:
            print(f"⚠️ Network info error: {e}")
        
        # Summary and recommendations
        print(f"\n📋 Performance Summary")
        print("=" * 30)
        print(f"Basic RPC: {basic_response_time*1000:.1f}ms ({perf_category})")
        if 'scan_response_time' in locals():
            print(f"scantxoutset: {scan_response_time:.1f}s ({scan_category})")
        print(f"Mempool: {mempool_info['size']:,} txs")
        print(f"Connections: {len(peer_info) if 'peer_info' in locals() else 'Unknown'}")
        
        print(f"\n💡 Dashboard Optimization Tips:")
        if basic_response_time > 0.1:
            print("• Consider restarting Bitcoin Core if consistently slow")
            print("• Check system resources (CPU, RAM, disk I/O)")
        
        if 'scan_response_time' in locals() and scan_response_time > 20:
            print("• Dashboard will automatically use slow address throttling")
            print("• Balance updates will be spaced 15+ minutes apart for slow addresses")
            print("• Consider using legacy wallet format for faster lookups")
        
        print(f"\n✅ Diagnostics complete!")
        
    except Exception as e:
        print(f"❌ Error connecting to Bitcoin Core: {e}")
        print(f"\n🔧 Troubleshooting:")
        print(f"1. Ensure Bitcoin Core is running")
        print(f"2. Check RPC credentials in bitcoin.conf")
        print(f"3. Verify RPC port (8332 for mainnet, 18332 for testnet)")
        print(f"4. Check firewall settings")

if __name__ == "__main__":
    test_node_performance()
