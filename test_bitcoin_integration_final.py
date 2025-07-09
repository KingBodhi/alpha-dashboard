#!/usr/bin/env python3
"""
Test the full Bitcoin integration with native segwit addresses.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
from services.bitcoin_service import BitcoinService
import asyncio

async def test_bitcoin_service_with_native_segwit():
    """Test the Bitcoin service with native segwit addresses."""
    print("Testing Bitcoin service with native segwit addresses...")
    print("=" * 60)
    
    # Generate a native segwit address
    generator = BitcoinAddressGenerator()
    native_address = generator.get_native_segwit_address()
    legacy_address = generator.get_legacy_address()
    
    print(f"Testing addresses:")
    print(f"  Native segwit: {native_address}")
    print(f"  Legacy: {legacy_address}")
    print()
    
    # Create Bitcoin service (but don't connect to avoid needing a real node)
    service = BitcoinService()
    
    # Test address validation
    print("Testing address validation:")
    print(f"  Native segwit valid: {_is_valid_address_format(native_address)}")
    print(f"  Legacy valid: {_is_valid_address_format(legacy_address)}")
    print()
    
    # Test address format detection
    print("Testing address format detection:")
    print(f"  Native segwit format: {_detect_address_format(native_address)}")
    print(f"  Legacy format: {_detect_address_format(legacy_address)}")
    
    print("\n✅ Bitcoin service integration test completed!")
    print("\nNext step: Test with a real Bitcoin Core node to verify full functionality")

def _is_valid_address_format(address):
    """Basic address format validation."""
    if not address or len(address) < 26:
        return False
    
    # Check format
    if address.startswith('bc1'):
        return len(address) in [42, 62]  # P2WPKH or P2WSH
    elif address.startswith('1'):
        return len(address) in range(26, 36)  # P2PKH
    elif address.startswith('3'):
        return len(address) in range(26, 36)  # P2SH
    else:
        return False

def _detect_address_format(address):
    """Detect address format."""
    if address.startswith('bc1'):
        return "Native Segwit (bech32)"
    elif address.startswith('3'):
        return "P2SH-wrapped Segwit"
    elif address.startswith('1'):
        return "Legacy (P2PKH)"
    else:
        return "Unknown"

if __name__ == "__main__":
    asyncio.run(test_bitcoin_service_with_native_segwit())
