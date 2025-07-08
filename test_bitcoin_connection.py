#!/usr/bin/env python3
"""
Test script to verify Bitcoin RPC connection.
Run this script to test if your Bitcoin node is accessible.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.bitcoin_service import BitcoinService
import time


def test_bitcoin_connection():
    """Test Bitcoin RPC connection and basic functionality."""
    print("🔗 Testing Bitcoin RPC Connection...")
    print("=" * 50)
    
    # Create service instance
    service = BitcoinService()
    
    # Test connection
    print("Attempting to connect...")
    success = service.connect_to_node()
    
    if not success:
        print("❌ Connection failed!")
        return False
    
    print("✅ Connection successful!")
    
    # Test basic RPC calls
    try:
        print("\n📊 Testing basic RPC calls...")
        
        # Get blockchain info
        blockchain_info = service.send_raw_command('getblockchaininfo')
        if blockchain_info:
            print(f"📦 Chain: {blockchain_info.get('chain', 'Unknown')}")
            print(f"📦 Blocks: {blockchain_info.get('blocks', 0):,}")
            print(f"📦 Headers: {blockchain_info.get('headers', 0):,}")
            print(f"📦 Best Block: {blockchain_info.get('bestblockhash', 'Unknown')[:16]}...")
        
        # Get network info
        network_info = service.send_raw_command('getnetworkinfo')
        if network_info:
            print(f"🌐 Version: {network_info.get('version', 'Unknown')}")
            print(f"🌐 Connections: {network_info.get('connections', 0)}")
        
        # Get mempool info
        mempool_info = service.send_raw_command('getmempoolinfo')
        if mempool_info:
            print(f"📋 Mempool Size: {mempool_info.get('size', 0):,} transactions")
            print(f"📋 Mempool Bytes: {mempool_info.get('bytes', 0):,} bytes")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        service.disconnect()


if __name__ == "__main__":
    print("Bitcoin RPC Connection Test")
    print("Make sure your Bitcoin node is running with RPC enabled.")
    print("Default settings: admin:admin123@127.0.0.1:8332")
    print()
    
    success = test_bitcoin_connection()
    
    if success:
        print("\n🎉 Your Bitcoin node is ready for the dashboard!")
    else:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure Bitcoin Core is running")
        print("2. Check bitcoin.conf has the correct RPC settings:")
        print("   rpcuser=admin")
        print("   rpcpassword=admin123")
        print("   rpcallowip=127.0.0.1")
        print("   rpcport=8332")
        print("   server=1")
        print("3. Update app/config/bitcoin_config.py if using different settings")
    
    sys.exit(0 if success else 1)
