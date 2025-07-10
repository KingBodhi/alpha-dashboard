#!/usr/bin/env python3
"""
Dashboard Performance Validator
Tests the optimized Bitcoin dashboard behavior with slow scantxoutset scenarios.
"""

import sys
import time
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_dashboard_optimization():
    """Test that the dashboard handles slow nodes gracefully."""
    print("🧪 Dashboard Performance Validation")
    print("=" * 50)
    
    try:
        from services.bitcoin_service import BitcoinService
        print("✅ BitcoinService imported successfully")
        
        # Create service instance
        service = BitcoinService()
        print("✅ BitcoinService initialized")
        
        # Test RPC connection
        print("\n📡 Testing RPC Connection...")
        if service.test_connection():
            print("✅ RPC connection successful")
        else:
            print("❌ RPC connection failed")
            print("💡 Ensure Bitcoin Core is running and RPC credentials are correct")
            return
        
        # Test slow address tracking
        print("\n⏱️ Testing Slow Address Tracking...")
        
        # Check if slow address tracking is initialized
        slow_addresses = getattr(service, '_slow_scan_addresses', {})
        print(f"📊 Current slow addresses: {len(slow_addresses)}")
        
        # Test address that will likely be slow
        test_address = "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"  # Example bech32
        print(f"🎯 Testing address: {test_address[:20]}...")
        
        # Start monitoring
        service.monitored_addresses.add(test_address)
        print(f"📍 Added address to monitoring list")
        
        # Simulate update cycle
        print(f"🔄 Running update cycle...")
        start_time = time.time()
        service.update_all_monitored_addresses()
        elapsed = time.time() - start_time
        
        print(f"⏱️ Update cycle completed in {elapsed:.1f}s")
        
        # Check if address was marked as slow
        updated_slow_addresses = getattr(service, '_slow_scan_addresses', {})
        if test_address in updated_slow_addresses:
            print(f"✅ Address correctly marked as slow")
            print(f"📅 Slow tracking enabled: {len(updated_slow_addresses)} total")
        else:
            print(f"ℹ️ Address not marked as slow (may be expected if scan was fast)")
        
        # Test throttling behavior
        print(f"\n⏳ Testing Throttling Behavior...")
        print(f"🔄 Running second update cycle...")
        start_time = time.time()
        service.update_all_monitored_addresses()
        elapsed = time.time() - start_time
        
        print(f"⏱️ Second update cycle: {elapsed:.1f}s")
        
        if elapsed < 1.0:
            print(f"✅ Throttling working - second cycle was fast (skipped slow address)")
        else:
            print(f"⚠️ Second cycle was also slow - may still be updating")
        
        # Summary
        print(f"\n📋 Validation Summary")
        print("=" * 30)
        print(f"Service Status: {'✅ Connected' if service.is_connected else '❌ Disconnected'}")
        print(f"Monitored Addresses: {len(service.monitored_addresses)}")
        print(f"Slow Addresses: {len(getattr(service, '_slow_scan_addresses', {}))}")
        print(f"Update Interval: {service.update_timer.interval()/1000}s")
        
        # Recommendations
        print(f"\n💡 Performance Tips:")
        print(f"• Dashboard will automatically throttle slow addresses")
        print(f"• Updates for slow addresses are spaced 15+ minutes apart")
        print(f"• Performance status shown in wallet widget")
        print(f"• Use legacy wallet format for faster balance checks if possible")
        
        print(f"\n✅ Dashboard optimization validation complete!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print(f"💡 Ensure all dependencies are installed: pip install -r requirements.txt")
    except Exception as e:
        print(f"❌ Validation error: {e}")
        print(f"💡 Check that Bitcoin Core is running and accessible")

def run_simple_performance_test():
    """Run a basic performance test of Bitcoin Core operations."""
    print("\n🚀 Quick Performance Test")
    print("=" * 30)
    
    try:
        from bitcoinrpc.authproxy import AuthServiceProxy
        from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
        
        # Connect to Bitcoin Core
        rpc_url = f"http://{BITCOIN_RPC_CONFIG['rpc_user']}:{BITCOIN_RPC_CONFIG['rpc_password']}@{BITCOIN_RPC_CONFIG['rpc_host']}:{BITCOIN_RPC_CONFIG['rpc_port']}"
        rpc = AuthServiceProxy(rpc_url, timeout=30)
        
        # Test basic operations
        operations = [
            ("getblockcount", lambda: rpc.getblockcount()),
            ("getbestblockhash", lambda: rpc.getbestblockhash()),
            ("getmempoolinfo", lambda: rpc.getmempoolinfo()),
        ]
        
        print("Testing basic RPC operations...")
        total_time = 0
        
        for op_name, op_func in operations:
            start_time = time.time()
            try:
                result = op_func()
                elapsed = time.time() - start_time
                total_time += elapsed
                
                if elapsed > 1.0:
                    status = "🐌 SLOW"
                elif elapsed > 0.1:
                    status = "⚠️ Moderate"
                else:
                    status = "✅ Fast"
                
                print(f"  {op_name}: {elapsed*1000:.1f}ms {status}")
                
            except Exception as e:
                print(f"  {op_name}: ❌ Failed - {e}")
        
        avg_time = total_time / len(operations)
        
        print(f"\nAverage response time: {avg_time*1000:.1f}ms")
        
        if avg_time < 0.05:
            print(f"🚀 Excellent node performance")
        elif avg_time < 0.2:
            print(f"✅ Good node performance")
        elif avg_time < 1.0:
            print(f"⚠️ Moderate node performance")
        else:
            print(f"🐌 Slow node - dashboard will automatically adapt")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")

if __name__ == "__main__":
    print("🔧 Alpha Dashboard Optimization Validator")
    print("This tool validates that the dashboard properly handles slow Bitcoin Core nodes")
    print()
    
    # Run basic performance test first
    run_simple_performance_test()
    
    # Run full validation
    validate_dashboard_optimization()
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Start the dashboard: python main.py")
    print(f"2. Click 'Connect' in the Bitcoin dashboard")
    print(f"3. Navigate to Profile page and set your Bitcoin address")
    print(f"4. Monitor performance indicators in the wallet widget")
    print(f"5. Check console output for throttling messages")
