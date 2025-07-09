#!/usr/bin/env python3
"""
Test script to verify that bitcoinlib can generate native segwit (bech32) addresses.
"""

from bitcoinlib.wallets import Wallet
from bitcoinlib.keys import HDKey
import os

def test_bitcoinlib_addresses():
    """Test native segwit address generation with bitcoinlib."""
    print("Testing Bitcoin address generation with bitcoinlib...")
    print("=" * 60)
    
    # Create a temporary wallet name
    wallet_name = "test_wallet_temp"
    
    # Remove any existing test wallet
    try:
        if os.path.exists(os.path.expanduser(f"~/.bitcoinlib/{wallet_name}.db")):
            os.remove(os.path.expanduser(f"~/.bitcoinlib/{wallet_name}.db"))
    except:
        pass
    
    try:
        # Create a new wallet with native segwit
        wallet = Wallet.create(wallet_name, network='bitcoin', witness_type='segwit')
        
        # Get the main key
        main_key = wallet.main_key
        
        print(f"Master Private Key: {main_key.wif}")
        print(f"Master Public Key: {main_key.public_hex}")
        print()
        
        # Generate addresses
        print("Generated addresses:")
        
        # Get the default address (should be native segwit)
        default_address = wallet.get_key().address
        print(f"Default address: {default_address}")
        
        # Generate a new address
        new_address = wallet.new_key().address
        print(f"New address: {new_address}")
        
        # Verify address types
        print()
        print("Address Type Analysis:")
        
        for addr in [default_address, new_address]:
            if addr.startswith('bc1'):
                print(f"✅ Native Segwit (bech32): {addr}")
            elif addr.startswith('3'):
                print(f"⚠️  P2SH-wrapped Segwit: {addr}")
            elif addr.startswith('1'):
                print(f"❌ Legacy (P2PKH): {addr}")
            else:
                print(f"❓ Unknown format: {addr}")
        
        print()
        print("SUCCESS: bitcoinlib can generate native segwit addresses!")
        
        # Clean up
        wallet.delete()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
def test_hd_key_direct():
    """Test HDKey direct generation."""
    print("\nTesting HDKey direct generation...")
    print("=" * 40)
    
    # Create a new HDKey
    key = HDKey()
    
    print(f"Private Key WIF: {key.wif}")
    print(f"Address (P2PKH): {key.address()}")
    
    # Generate segwit address
    try:
        segwit_addr = key.address(script_type='p2wpkh')
        print(f"Native Segwit: {segwit_addr}")
    except Exception as e:
        print(f"Error generating native segwit: {e}")
    
    # Generate P2SH-wrapped segwit
    try:
        p2sh_segwit_addr = key.address(script_type='p2sh-p2wpkh')
        print(f"P2SH-wrapped Segwit: {p2sh_segwit_addr}")
    except Exception as e:
        print(f"Error generating P2SH-wrapped segwit: {e}")

if __name__ == "__main__":
    test_bitcoinlib_addresses()
    test_hd_key_direct()
