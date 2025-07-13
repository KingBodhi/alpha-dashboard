#!/usr/bin/env python3
"""
Bitcoin Core descriptor-based address generator.
This utility generates addresses using Bitcoin Core's wallet descriptors
instead of standalone key generation.
"""

import logging
from typing import Tuple, Optional, Dict, List
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

logger = logging.getLogger(__name__)


class BitcoinWalletDescriptorGenerator:
    """
    Bitcoin address generator that uses Bitcoin Core's wallet descriptors.
    This integrates with the loaded wallet in Bitcoin Core rather than
    generating standalone addresses.
    """
    
    def __init__(self, bitcoin_service=None, wallet_name=None):
        """
        Initialize the descriptor-based address generator.
        
        Args:
            bitcoin_service: Reference to the BitcoinService instance
            wallet_name: Name of the wallet to use (optional)
        """
        self.bitcoin_service = bitcoin_service
        self.wallet_name = wallet_name or "dashboard_wallet"
        self.wallet_info = None
        self.descriptors = {}
        self.addresses = {}
        
    def ensure_wallet_connection(self):
        """Ensure we have a connection to Bitcoin Core and a wallet loaded."""
        if not self.bitcoin_service or not self.bitcoin_service.is_connected:
            raise ConnectionError("Bitcoin Core not connected")
            
        # Ensure wallet is loaded
        if not self.bitcoin_service.ensure_wallet_loaded():
            raise RuntimeError("No wallet available in Bitcoin Core")
            
        return True
    
    def get_wallet_info(self):
        """Get wallet information including descriptor status."""
        try:
            self.ensure_wallet_connection()
            
            # Get wallet info
            wallet_info = self.bitcoin_service._safe_rpc_call(
                lambda: self.bitcoin_service.rpc_connection.getwalletinfo()
            )
            
            if not wallet_info:
                raise RuntimeError("Could not get wallet information")
                
            self.wallet_info = wallet_info
            
            # Check if it's a descriptor wallet
            is_descriptor = wallet_info.get('descriptors', False)
            if not is_descriptor:
                logger.warning("Wallet is not a descriptor wallet - some features may be limited")
            
            return wallet_info
            
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            raise
    
    def get_wallet_descriptors(self):
        """Get all descriptors from the loaded wallet."""
        try:
            self.ensure_wallet_connection()
            
            # Get descriptors (only works for descriptor wallets)
            descriptors = self.bitcoin_service._safe_rpc_call(
                lambda: self.bitcoin_service.rpc_connection.listdescriptors()
            )
            
            if descriptors:
                self.descriptors = descriptors
                logger.info(f"Retrieved {len(descriptors.get('descriptors', []))} wallet descriptors")
                return descriptors
            else:
                logger.warning("Could not retrieve wallet descriptors - may not be a descriptor wallet")
                return None
                
        except Exception as e:
            logger.warning(f"Error getting descriptors (wallet may not support them): {e}")
            return None
    
    def generate_new_address(self, address_type='bech32', label=None):
        """
        Generate a new address from the wallet.
        
        Args:
            address_type: 'legacy', 'p2sh-segwit', or 'bech32'
            label: Optional label for the address
            
        Returns:
            New address string
        """
        try:
            self.ensure_wallet_connection()
            
            # Map address types to Bitcoin Core parameters
            address_type_map = {
                'legacy': 'legacy',
                'p2sh-segwit': 'p2sh-segwit', 
                'bech32': 'bech32',
                'native-segwit': 'bech32'
            }
            
            core_type = address_type_map.get(address_type, 'bech32')
            
            # Generate new address
            if label:
                address = self.bitcoin_service._safe_rpc_call(
                    lambda: self.bitcoin_service.rpc_connection.getnewaddress(label, core_type)
                )
            else:
                address = self.bitcoin_service._safe_rpc_call(
                    lambda: self.bitcoin_service.rpc_connection.getnewaddress("", core_type)
                )
            
            if address:
                # Store the address with its type
                self.addresses[address] = {
                    'type': address_type,
                    'label': label,
                    'generated_time': None  # Could add timestamp if needed
                }
                
                logger.info(f"Generated new {address_type} address: {address[:16]}...")
                return address
            else:
                raise RuntimeError(f"Failed to generate {address_type} address")
                
        except Exception as e:
            logger.error(f"Error generating new address: {e}")
            raise
    
    def get_wallet_addresses(self, include_change=False):
        """
        Get all addresses from the wallet.
        
        Args:
            include_change: Whether to include change addresses
            
        Returns:
            List of addresses with their information
        """
        try:
            self.ensure_wallet_connection()
            
            addresses = []
            
            # Get receiving addresses
            receiving_addresses = self.bitcoin_service._safe_rpc_call(
                lambda: self.bitcoin_service.rpc_connection.getaddressesbylabel("")
            )
            
            if receiving_addresses:
                for addr, info in receiving_addresses.items():
                    addr_info = self.get_address_info(addr)
                    addresses.append({
                        'address': addr,
                        'type': self._detect_address_type(addr),
                        'purpose': 'receive',
                        'info': addr_info
                    })
            
            # Get change addresses if requested
            if include_change:
                try:
                    change_addresses = self.bitcoin_service._safe_rpc_call(
                        lambda: self.bitcoin_service.rpc_connection.getrawchangeaddress()
                    )
                    if change_addresses:
                        addr_info = self.get_address_info(change_addresses)
                        addresses.append({
                            'address': change_addresses,
                            'type': self._detect_address_type(change_addresses),
                            'purpose': 'change',
                            'info': addr_info
                        })
                except Exception:
                    pass  # Change addresses might not be available
            
            return addresses
            
        except Exception as e:
            logger.error(f"Error getting wallet addresses: {e}")
            return []
    
    def get_address_info(self, address):
        """Get detailed information about an address."""
        try:
            self.ensure_wallet_connection()
            
            # Get address info from Bitcoin Core
            addr_info = self.bitcoin_service._safe_rpc_call(
                lambda: self.bitcoin_service.rpc_connection.getaddressinfo(address)
            )
            
            return addr_info
            
        except Exception as e:
            logger.warning(f"Could not get info for address {address[:16]}...: {e}")
            return None
    
    def _detect_address_type(self, address):
        """Detect the type of address based on its format."""
        if address.startswith('bc1') or address.startswith('tb1'):
            return 'bech32'
        elif address.startswith('3') or address.startswith('2'):
            return 'p2sh-segwit'
        elif address.startswith('1'):
            return 'legacy'
        else:
            return 'unknown'
    
    def get_primary_address(self, preferred_type='bech32'):
        """
        Get or generate a primary address for the wallet.
        
        Args:
            preferred_type: Preferred address type ('bech32', 'p2sh-segwit', 'legacy')
            
        Returns:
            Primary address string
        """
        try:
            # First try to get existing addresses
            addresses = self.get_wallet_addresses()
            
            # Look for an address of the preferred type
            for addr_data in addresses:
                if addr_data['type'] == preferred_type and addr_data['purpose'] == 'receive':
                    logger.info(f"Using existing {preferred_type} address: {addr_data['address'][:16]}...")
                    return addr_data['address']
            
            # If no address of preferred type exists, generate one
            logger.info(f"No existing {preferred_type} address found, generating new one...")
            return self.generate_new_address(preferred_type, "Primary Dashboard Address")
            
        except Exception as e:
            logger.error(f"Error getting primary address: {e}")
            raise
    
    def get_all_address_types(self, base_address=None):
        """
        Get addresses of all types from the wallet.
        
        Returns:
            Dictionary with all address types available in the wallet
        """
        try:
            addresses = {
                'bech32': None,
                'p2sh_segwit': None,  
                'legacy': None
            }
            
            # Get existing addresses
            wallet_addresses = self.get_wallet_addresses()
            
            # Fill in existing addresses by type
            for addr_data in wallet_addresses:
                addr_type = addr_data['type']
                if addr_type == 'bech32' and not addresses['bech32']:
                    addresses['bech32'] = addr_data['address']
                elif addr_type == 'p2sh-segwit' and not addresses['p2sh_segwit']:
                    addresses['p2sh_segwit'] = addr_data['address']
                elif addr_type == 'legacy' and not addresses['legacy']:
                    addresses['legacy'] = addr_data['address']
            
            # Generate missing address types
            if not addresses['bech32']:
                addresses['bech32'] = self.generate_new_address('bech32', 'Dashboard Native SegWit')
            if not addresses['p2sh_segwit']:
                addresses['p2sh_segwit'] = self.generate_new_address('p2sh-segwit', 'Dashboard P2SH SegWit')
            if not addresses['legacy']:
                addresses['legacy'] = self.generate_new_address('legacy', 'Dashboard Legacy')
            
            return addresses
            
        except Exception as e:
            logger.error(f"Error getting all address types: {e}")
            raise
    
    def validate_address_ownership(self, address):
        """
        Validate that an address belongs to the loaded wallet.
        
        Args:
            address: Address to validate
            
        Returns:
            True if address belongs to wallet, False otherwise
        """
        try:
            self.ensure_wallet_connection()
            
            addr_info = self.get_address_info(address)
            if addr_info:
                return addr_info.get('ismine', False)
            
            return False
            
        except Exception as e:
            logger.warning(f"Error validating address ownership: {e}")
            return False


def test_descriptor_generator(bitcoin_service):
    """Test the descriptor-based address generator.

    Args:
        bitcoin_service: Shared BitcoinService instance (must be provided).
    """
    print("Testing BitcoinWalletDescriptorGenerator...")
    print("=" * 60)

    try:
        # Always require explicit BitcoinService instance
        print("✅ Using shared BitcoinService instance")

        # Create descriptor generator
        generator = BitcoinWalletDescriptorGenerator(bitcoin_service)

        # Test wallet info
        print("Getting wallet info...")
        wallet_info = generator.get_wallet_info()
        print(f"Wallet name: {wallet_info.get('walletname', 'default')}")
        print(f"Descriptor wallet: {wallet_info.get('descriptors', False)}")
        print(f"Balance: {wallet_info.get('balance', 0)} BTC")
        print()

        # Test descriptors (if supported)
        print("Getting wallet descriptors...")
        descriptors = generator.get_wallet_descriptors()
        if descriptors:
            desc_list = descriptors.get('descriptors', [])
            print(f"Found {len(desc_list)} descriptors")
            for i, desc in enumerate(desc_list[:3]):  # Show first 3
                print(f"  {i+1}. {desc.get('desc', '')[:50]}...")
        else:
            print("No descriptors available (legacy wallet)")
        print()

        # Test getting existing addresses
        print("Getting existing wallet addresses...")
        addresses = generator.get_wallet_addresses()
        print(f"Found {len(addresses)} addresses:")
        for addr_data in addresses[:5]:  # Show first 5
            print(f"  {addr_data['type']}: {addr_data['address']}")
        print()

        # Test primary address
        print("Getting primary address...")
        primary = generator.get_primary_address('bech32')
        print(f"Primary bech32 address: {primary}")
        print()

        # Test all address types
        print("Getting all address types...")
        all_addresses = generator.get_all_address_types()
        for addr_type, address in all_addresses.items():
            ownership = generator.validate_address_ownership(address)
            print(f"  {addr_type}: {address} (owned: {ownership})")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_descriptor_generator()