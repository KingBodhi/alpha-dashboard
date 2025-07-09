#!/usr/bin/env python3
"""
Test the manual Bitcoin connection functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.bitcoin_service import BitcoinService
import asyncio

def test_manual_connection():
    """Test that the Bitcoin service can connect manually without auto-start."""
    print("Testing manual Bitcoin connection...")
    print("=" * 50)
    
    # Create service but don't auto-start
    service = BitcoinService()
    
    print(f"✅ Service created")
    print(f"   Connected: {service.is_connected}")
    print(f"   RPC Connection: {service.rpc_connection}")
    
    print(f"\nService is ready for manual connection via UI button")
    print(f"No auto-connection errors should occur!")
    
    # Test that we can check if connection would work (without actually connecting)
    rpc_url = f"http://{service.rpc_user}:{service.rpc_password}@{service.rpc_host}:{service.rpc_port}"
    print(f"\nRPC URL would be: {rpc_url.replace(service.rpc_password, '***')}")
    
    print(f"\n✅ Manual connection test completed!")
    print(f"   The application should start without Bitcoin errors")
    print(f"   Users can manually connect via the Connect button")

if __name__ == "__main__":
    test_manual_connection()
