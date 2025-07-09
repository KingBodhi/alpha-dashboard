import json
import threading
import time
import platform
import os
import logging
from decimal import Decimal
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG, UI_CONFIG

# Try to import psutil for system monitoring, fallback if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️ psutil not available - system monitoring disabled")

# Set up logging
logger = logging.getLogger(__name__)


class BitcoinService(QObject):
    """Service to handle Bitcoin RPC connections with adaptive performance handling."""
    
    # Signals for UI updates
    connection_status_changed = pyqtSignal(bool)  # True if connected, False if disconnected
    blockchain_info_updated = pyqtSignal(dict)   # Latest blockchain info
    new_block_received = pyqtSignal(dict)        # New block data
    mempool_updated = pyqtSignal(dict)           # Mempool statistics
    network_info_updated = pyqtSignal(dict)     # Network information
    peer_info_updated = pyqtSignal(list)        # Connected peers
    error_occurred = pyqtSignal(str)            # Error messages
    status_message = pyqtSignal(str)            # Status updates
    
    # Address-specific signals
    address_balance_updated = pyqtSignal(str, dict)  # address, balance_info
    address_transactions_updated = pyqtSignal(str, list)  # address, transactions
    
    # Transaction-related signals
    transaction_created = pyqtSignal(str)  # raw transaction hex
    transaction_signed = pyqtSignal(str)   # signed transaction hex
    transaction_broadcasted = pyqtSignal(str)  # transaction ID
    transaction_error = pyqtSignal(str)    # error message
    fee_estimated = pyqtSignal(dict)       # fee estimation data
    
    def __init__(self, rpc_user=None, rpc_password=None, 
                 rpc_host=None, rpc_port=None):
        super().__init__()
        
        # RPC connection parameters (use config defaults if not provided)
        self.rpc_user = rpc_user or BITCOIN_RPC_CONFIG["rpc_user"]
        self.rpc_password = rpc_password or BITCOIN_RPC_CONFIG["rpc_password"]
        self.rpc_host = rpc_host or BITCOIN_RPC_CONFIG["rpc_host"]
        self.rpc_port = rpc_port or BITCOIN_RPC_CONFIG["rpc_port"]
        
        # Connection state
        self.rpc_connection = None
        self.is_connected = False
        self.last_block_hash = None
        
        # Address monitoring
        self.monitored_addresses = set()
        self.address_balances = {}
        self.address_transactions = {}
        
        # Wallet type detection
        self.is_descriptor_wallet = False
        self.last_blockchain_info = {}
        
        # Adaptive settings based on system capabilities
        self.is_low_power_device = self._detect_low_power_device()
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.node_busy = False
        
        # Adaptive timeouts based on device type
        if self.is_low_power_device:
            self.base_timeout = 45
            self.connection_timeout = 60
            self.update_interval = 30000  # 30 seconds - much slower
            self.max_retries = 8
            self.retry_delay = 5
            print("🔧 Low-power device detected - using extended timeouts")
        else:
            self.base_timeout = 15
            self.connection_timeout = 30
            self.update_interval = 15000  # 15 seconds - slower than before
            self.max_retries = 5
            self.retry_delay = 3
        
        # Performance tracking
        self.rpc_call_times = []
        self.slow_call_threshold = 10 if self.is_low_power_device else 5
        
        # Update timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.setInterval(self.update_interval)
        
        # Background thread for blocking operations
        self.worker_thread = None
        self.should_stop = False
        
    def _detect_low_power_device(self):
        """Detect if running on a low-power device like Raspberry Pi."""
        try:
            # Quick check for ARM architecture first (fastest)
            machine = platform.machine().lower()
            if 'arm' in machine or 'aarch64' in machine:
                return True
            
            # Quick memory check if psutil is available
            if HAS_PSUTIL:
                try:
                    memory_gb = psutil.virtual_memory().total / (1024**3)
                    if memory_gb < 4:  # Less than 4GB RAM
                        return True
                except:
                    pass
            
            # Only check /proc/cpuinfo if the above didn't detect low power
            if os.path.exists('/proc/cpuinfo'):
                try:
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read(1024).lower()  # Only read first 1KB
                        if 'raspberry pi' in cpuinfo or 'bcm' in cpuinfo:
                            return True
                except:
                    pass
            
            return False
            
        except Exception:
            # If any detection fails, assume standard device
            return False
    
    def _check_system_resources(self):
        """Check system resources and adjust timeouts if needed."""
        if not HAS_PSUTIL:
            return True
            
        try:
            # Check memory and CPU usage
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Adjust timeouts based on system load
            if memory.percent > 85 or cpu_percent > 90:
                self.base_timeout = min(120, self.base_timeout * 1.5)
                self.status_message.emit("⚠️ High system load detected - adjusting timeouts")
                return False
            
            return True
            
        except Exception:
            return True
        
    def connect_to_node(self):
        """Establish connection to Bitcoin node with adaptive retry logic."""
        for attempt in range(self.max_retries):
            try:
                self.status_message.emit(f"Connecting... (attempt {attempt + 1}/{self.max_retries})")
                
                # Check system resources before attempting connection
                self._check_system_resources()
                
                # Test basic connectivity first
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                
                try:
                    result = sock.connect_ex((self.rpc_host, self.rpc_port))
                    if result != 0:
                        raise ConnectionError(f"Cannot connect to {self.rpc_host}:{self.rpc_port}")
                finally:
                    sock.close()
                
                # Create RPC connection with adaptive timeout
                rpc_url = f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}"
                self.rpc_connection = AuthServiceProxy(rpc_url, timeout=self.base_timeout)
                
                # Test connection with a simple call
                start_time = time.time()
                info = self.rpc_connection.getblockchaininfo()
                call_time = time.time() - start_time
                
                # Track performance and adjust timeouts
                if call_time > self.slow_call_threshold:
                    self.base_timeout = min(120, self.base_timeout * 1.2)
                    print(f"⚠️ Slow RPC call detected ({call_time:.1f}s) - adjusting timeout to {self.base_timeout}s")
                
                self.is_connected = True
                self.consecutive_failures = 0
                self.connection_status_changed.emit(True)
                
                # Check if node is syncing
                verification_progress = info.get('verificationprogress', 1.0)
                if verification_progress < 0.999:
                    self.node_busy = True
                    self.status_message.emit("🔄 Bitcoin node is syncing - using reduced update frequency")
                else:
                    self.node_busy = False
                    self.status_message.emit("✅ Connected successfully!")
                
                print(f"✅ Connected to Bitcoin node at {self.rpc_host}:{self.rpc_port}")
                print(f"📊 Chain: {info.get('chain', 'unknown')}")
                print(f"📦 Blocks: {info.get('blocks', 0)}")
                
                # Detect wallet type
                self._detect_wallet_type()
                
                return True
                
            except JSONRPCException as e:
                error_msg = f"RPC Error: {e.error['message']}"
                print(f"❌ {error_msg}")
                if "unauthorized" in error_msg.lower():
                    self.error_occurred.emit("Authentication failed. Check RPC username/password.")
                    break
                    
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Connection attempt {attempt + 1} failed: {error_msg}")
                
                if "timeout" in error_msg.lower():
                    self.status_message.emit(f"Timeout (attempt {attempt + 1}) - Bitcoin node may be busy")
                elif "connection refused" in error_msg.lower():
                    self.status_message.emit(f"Connection refused (attempt {attempt + 1}) - Is Bitcoin Core running?")
                else:
                    self.status_message.emit(f"Error: {error_msg}")
            
            # Wait before retry with progressive backoff
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay + (attempt * 2)
                self.status_message.emit(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # All attempts failed
        self.is_connected = False
        self.connection_status_changed.emit(False)
        self.status_message.emit("❌ Failed to connect after all attempts")
        self.error_occurred.emit("Failed to connect to Bitcoin node. Check if Bitcoin Core is running and RPC is properly configured.")
        return False
    
    def disconnect(self):
        """Disconnect from Bitcoin node."""
        self.should_stop = True
        self.update_timer.stop()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)
            
        self.is_connected = False
        self.rpc_connection = None
        self.connection_status_changed.emit(False)
        print("🔌 Disconnected from Bitcoin node")
    
    def start_monitoring(self):
        """Start monitoring Bitcoin node for updates."""
        if not self.is_connected:
            if not self.connect_to_node():
                return False
        
        # Start periodic updates
        self.update_timer.start()
        
        # Start background monitoring thread
        self.should_stop = False
        self.worker_thread = threading.Thread(target=self._monitor_blocks, daemon=True)
        self.worker_thread.start()
        
        print("🔍 Started monitoring Bitcoin node")
        return True
    
    def update_data(self):
        """Update various Bitcoin node data with adaptive error handling."""
        if not self.is_connected or not self.rpc_connection:
            return
        
        try:
            # Always try to get blockchain info first
            blockchain_info = self._safe_rpc_call(self.rpc_connection.getblockchaininfo)
            if blockchain_info:
                self.last_blockchain_info = blockchain_info
                self.blockchain_info_updated.emit(blockchain_info)
                self.consecutive_failures = 0
                self._adjust_update_frequency(success=True)
                
                # Check if node is busy syncing
                verification_progress = blockchain_info.get('verificationprogress', 1.0)
                blocks = blockchain_info.get('blocks', 0)
                headers = blockchain_info.get('headers', 0)
                
                self.node_busy = verification_progress < 0.999 or headers > blocks
                
                if self.node_busy:
                    self.status_message.emit("🔄 Node syncing - limited updates")
                    # Only update blockchain info when syncing to reduce load
                    return
                else:
                    self.status_message.emit("✅ Updated successfully")
            else:
                # Failed to get blockchain info - node may be busy
                self._adjust_update_frequency(success=False)
                self.status_message.emit("⚠️ Bitcoin Core is busy - reducing update frequency")
                return
            
            # Only get other info if node is not busy
            if not self.node_busy:
                # Get network info
                network_info = self._safe_rpc_call(self.rpc_connection.getnetworkinfo)
                if network_info:
                    self.network_info_updated.emit(network_info)
                
                # Get mempool info
                mempool_info = self._safe_rpc_call(self.rpc_connection.getmempoolinfo)
                if mempool_info:
                    self.mempool_updated.emit(mempool_info)
                
                # Get peer info (limit to prevent UI overload)
                peer_info = self._safe_rpc_call(
                    lambda: self.rpc_connection.getpeerinfo()[:UI_CONFIG["max_peers_display"]]
                )
                if peer_info:
                    self.peer_info_updated.emit(peer_info)
                
                # Update monitored addresses
                self.update_all_monitored_addresses()
            
        except Exception as e:
            self._handle_update_error(e)
    
    def _safe_rpc_call(self, rpc_func_or_method, params=None, timeout_override=None):
        """Make RPC call with timeout and error handling."""
        try:
            timeout = timeout_override or self.base_timeout
            
            # Handle both callable functions and method names with parameters
            start_time = time.time()
            if callable(rpc_func_or_method):
                result = rpc_func_or_method()
            else:
                # Method name with parameters
                method = getattr(self.rpc_connection, rpc_func_or_method)
                if params:
                    result = method(*params)
                else:
                    result = method()
            
            call_time = time.time() - start_time
            
            # Track slow calls
            if call_time > self.slow_call_threshold:
                print(f"⚠️ Slow RPC call: {call_time:.1f}s")
            
            return result
            
        except JSONRPCException as e:
            # Just return None silently for common busy node errors
            error_msg = str(e)
            if any(x in error_msg for x in ["Request-sent", "Work queue", "timeout", "busy"]):
                return None
            # Only log unexpected errors
            print(f"RPC Error: {e.error.get('message', error_msg) if hasattr(e, 'error') else error_msg}")
            return None
        except Exception as e:
            error_str = str(e)
            # Silently handle common timeout/busy errors
            if any(x in error_str.lower() for x in ["timeout", "connection", "request-sent"]):
                return None
            # Only log unexpected errors
            print(f"RPC call failed: {error_str}")
            return None
    
    def _handle_update_error(self, error):
        """Handle update errors with adaptive behavior."""
        self.consecutive_failures += 1
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            if self.consecutive_failures <= self.max_consecutive_failures:
                print(f"⏰ Update timeout (failure {self.consecutive_failures})")
                self.status_message.emit(f"⏰ Timeout - Bitcoin node may be busy")
                # Don't disconnect on timeout, just skip this update
                return
            else:
                self.status_message.emit("❌ Multiple timeouts - adjusting settings")
                # Increase timeout for future calls
                self.base_timeout = min(120, self.base_timeout * 1.5)
                self.consecutive_failures = 0
        elif "connection" in error_str:
            print(f"❌ Connection lost: {error}")
            self.is_connected = False
            self.connection_status_changed.emit(False)
            self.status_message.emit("❌ Connection lost - attempting to reconnect")
            
            # Try to reconnect
            self.start_monitoring()
        else:
            print(f"❌ Update error: {error}")
            self.status_message.emit(f"❌ Update error: {str(error)}")
        
        # Reset failure count if too many
        if self.consecutive_failures > self.max_consecutive_failures:
            self.consecutive_failures = 0
    
    def _monitor_blocks(self):
        """Monitor for new blocks in background thread."""
        while not self.should_stop and self.is_connected:
            try:
                if not self.rpc_connection:
                    break
                    
                # Get latest block hash
                current_hash = self._safe_rpc_call(self.rpc_connection.getbestblockhash)
                
                if current_hash:
                    # Check if we have a new block
                    if self.last_block_hash and current_hash != self.last_block_hash:
                        # Get block details
                        block_data = self._safe_rpc_call(lambda: self.rpc_connection.getblock(current_hash))
                        if block_data:
                            self.new_block_received.emit(block_data)
                            print(f"🔗 New block: {current_hash[:16]}... (Height: {block_data.get('height', 'unknown')})")
                    
                    self.last_block_hash = current_hash
                
                # Sleep for a bit before checking again
                time.sleep(5)  # Longer sleep to reduce load
                
            except Exception as e:
                # Silently handle errors in background thread
                time.sleep(10)  # Wait longer on error
    
    def get_block_by_hash(self, block_hash):
        """Get detailed block information by hash."""
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
            return self.rpc_connection.getblock(block_hash, 2)  # Verbose level 2 for full details
        except Exception as e:
            print(f"❌ Error getting block {block_hash}: {e}")
            return None
    
    def get_transaction(self, txid):
        """Get transaction details."""
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
            return self.rpc_connection.getrawtransaction(txid, True)
        except Exception as e:
            print(f"❌ Error getting transaction {txid}: {e}")
            return None
    
    def send_raw_command(self, method, *params):
        """Send a raw RPC command."""
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
            return getattr(self.rpc_connection, method)(*params)
        except Exception as e:
            print(f"❌ Error executing {method}: {e}")
            return None

    def add_address_to_monitor(self, address):
        """Add a Bitcoin address to monitor for balance and transactions."""
        if address and address not in self.monitored_addresses:
            self.monitored_addresses.add(address)
            self.address_balances[address] = Decimal('0')
            self.address_transactions[address] = []
            print(f"📍 Now monitoring address: {address}")
            
            # Update balance immediately if connected
            if self.is_connected:
                self.update_address_balance(address)
    
    def remove_address_from_monitor(self, address):
        """Remove a Bitcoin address from monitoring."""
        if address in self.monitored_addresses:
            self.monitored_addresses.remove(address)
            self.address_balances.pop(address, None)
            self.address_transactions.pop(address, None)
            print(f"📍 Stopped monitoring address: {address}")
    
    def update_address_balance(self, address):
        """Update balance for a specific address."""
        if not self.is_connected or not self.rpc_connection:
            return
            
        try:
            # Try different methods depending on Bitcoin Core version and wallet type
            balance_btc = Decimal('0')
            utxo_count = 0
            
            # Method 1: Try scantxoutset (works with any address, no import needed)
            try:
                scan_result = self._safe_rpc_call(
                    lambda: self.rpc_connection.scantxoutset("start", [f"addr({address})"])
                )
                if scan_result:
                    balance_btc = Decimal(str(scan_result.get('total_amount', 0)))
                    utxo_count = len(scan_result.get('unspents', []))
                    print(f"📊 scantxoutset result for {address}: {balance_btc:.8f} BTC ({utxo_count} UTXOs)")
                else:
                    print(f"⚠️ scantxoutset failed for {address}")
                    
            except Exception as e:
                print(f"⚠️ scantxoutset not available: {e}")
                
                # Method 2: Try listunspent (requires imported address)
                try:
                    # First try to import the address (works with legacy wallets)
                    try:
                        self.rpc_connection.importaddress(address, "", False)
                        print(f"✅ Imported address {address}")
                    except JSONRPCException as import_error:
                        if "already exists" in str(import_error).lower():
                            print(f"📍 Address {address} already imported")
                        elif "descriptor wallet" in str(import_error).lower():
                            print(f"⚠️ Descriptor wallet detected - using alternative method")
                            # For descriptor wallets, we'll use scantxoutset which we already tried
                            balance_btc = Decimal('0')
                        else:
                            print(f"⚠️ Could not import address {address}: {import_error}")
                    
                    # Try listunspent for imported address
                    if balance_btc == 0:  # Only if scantxoutset didn't work
                        unspent = self._safe_rpc_call(lambda: self.rpc_connection.listunspent(0, 9999999, [address]))
                        if unspent is not None:
                            balance_btc = sum(Decimal(str(utxo['amount'])) for utxo in unspent)
                            utxo_count = len(unspent)
                            print(f"📊 listunspent result for {address}: {balance_btc:.8f} BTC ({utxo_count} UTXOs)")
                        
                except Exception as e2:
                    print(f"⚠️ listunspent failed for {address}: {e2}")
            
            # Update stored balance
            self.address_balances[address] = balance_btc
            
            # Get current Bitcoin price for USD conversion
            btc_price_usd = self.get_btc_price_estimate()
            balance_usd = float(balance_btc) * btc_price_usd
            
            balance_info = {
                'balance_btc': balance_btc,
                'balance_usd': balance_usd,
                'confirmed': balance_btc,  # For now, treat all as confirmed
                'unconfirmed': Decimal('0'),
                'utxo_count': utxo_count,
                'last_updated': time.time()
            }
            
            # Emit signal with balance update
            self.address_balance_updated.emit(address, balance_info)
            print(f"💰 Balance updated for {address}: {balance_btc:.8f} BTC (${balance_usd:.2f})")
                
        except Exception as e:
            print(f"❌ Error updating balance for {address}: {e}")
            # Emit zero balance on error
            balance_info = {
                'balance_btc': Decimal('0'),
                'balance_usd': 0.0,
                'confirmed': Decimal('0'),
                'unconfirmed': Decimal('0'),
                'utxo_count': 0,
                'last_updated': time.time(),
                'error': str(e)
            }
            self.address_balance_updated.emit(address, balance_info)
    
    def get_btc_price_estimate(self):
        """Get Bitcoin price estimate (placeholder - would use real API)."""
        # This is a placeholder. In a real implementation, you'd fetch from an API
        return 45000.0  # Example BTC price in USD
    
    def update_address_transactions(self, address):
        """Update transaction history for a specific address."""
        if not self.is_connected or not self.rpc_connection:
            return
            
        try:
            # Get transactions for this address
            # Note: This requires the address to be in the wallet or using a block explorer API
            transactions = []
            
            # For now, we'll create placeholder transactions when balance changes
            # In a full implementation, this would scan the blockchain or use an API
            
            if address in self.address_balances and self.address_balances[address] > 0:
                # Create a placeholder transaction
                placeholder_tx = {
                    'txid': f'demo_tx_{address[:8]}',
                    'amount': self.address_balances[address],
                    'confirmations': 6,
                    'time': int(time.time()),
                    'type': 'receive',
                    'address': address
                }
                transactions = [placeholder_tx]
            
            self.address_transactions[address] = transactions
            self.address_transactions_updated.emit(address, transactions)
            
        except Exception as e:
            print(f"❌ Error updating transactions for {address}: {e}")
    
    def update_all_monitored_addresses(self):
        """Update all monitored addresses."""
        for address in self.monitored_addresses:
            self.update_address_balance(address)
            self.update_address_transactions(address)
    
    def _adjust_update_frequency(self, success=True):
        """Dynamically adjust update frequency based on node responsiveness."""
        if success:
            # Gradually return to normal frequency if things are working well
            if self.update_timer.interval() > self.update_interval:
                new_interval = max(self.update_interval, self.update_timer.interval() - 2000)
                self.update_timer.setInterval(new_interval)
                if new_interval != self.update_timer.interval():
                    print(f"📈 Update frequency increased to {new_interval/1000}s")
        else:
            # Slow down updates when having issues
            current_interval = self.update_timer.interval()
            max_interval = 60000 if self.is_low_power_device else 30000  # 60s or 30s max
            new_interval = min(max_interval, current_interval + 5000)
            
            if new_interval != current_interval:
                self.update_timer.setInterval(new_interval)
                print(f"📉 Update frequency reduced to {new_interval/1000}s due to node being busy")
    
    def _update_data_background(self):
        """Run update_data in background thread to prevent UI blocking."""
        if not self.is_connected or not self.rpc_connection:
            return
        
        # Run in background thread to prevent UI blocking
        def background_update():
            try:
                self.update_data_sync()
            except Exception as e:
                self._handle_update_error(e)
        
        # Create and start background thread
        update_thread = threading.Thread(target=background_update, daemon=True)
        update_thread.start()

    # =====================================================================
    # TRANSACTION FUNCTIONALITY
    # =====================================================================
    
    def estimate_fee(self, target_blocks=6):
        """Estimate transaction fee for confirmation in target blocks"""
        try:
            # Try smart fee estimation first
            result = self._safe_rpc_call('estimatesmartfee', [target_blocks])
            if result and 'feerate' in result:
                fee_data = {
                    'feerate': result['feerate'],
                    'blocks': target_blocks,
                    'errors': result.get('errors', [])
                }
                self.fee_estimated.emit(fee_data)
                return fee_data
            
            # Fallback to older method
            result = self._safe_rpc_call('estimatefee', [target_blocks])
            if result and result > 0:
                fee_data = {
                    'feerate': result,
                    'blocks': target_blocks,
                    'errors': []
                }
                self.fee_estimated.emit(fee_data)
                return fee_data
            
            # Default fallback fee
            fee_data = {
                'feerate': 0.00001,  # 1 sat/byte
                'blocks': target_blocks,
                'errors': ['Fee estimation unavailable, using default']
            }
            self.fee_estimated.emit(fee_data)
            return fee_data
            
        except Exception as e:
            logger.error(f"Error estimating fee: {e}")
            error_msg = f"Fee estimation failed: {str(e)}"
            self.transaction_error.emit(error_msg)
            return None
    
    def get_unspent_outputs(self, address, min_confirmations=1):
        """Get unspent transaction outputs for an address"""
        try:
            # For descriptor wallets, use scantxoutset
            if self.is_descriptor_wallet:
                result = self._safe_rpc_call('scantxoutset', ['start', [f"addr({address})"]])
                if result and 'unspents' in result:
                    utxos = []
                    for utxo in result['unspents']:
                        if utxo.get('height', 0) > 0:  # Confirmed transactions
                            confirmations = self.last_blockchain_info.get('blocks', 0) - utxo['height'] + 1
                            if confirmations >= min_confirmations:
                                utxos.append({
                                    'txid': utxo['txid'],
                                    'vout': utxo['vout'],
                                    'amount': utxo['amount'],
                                    'scriptPubKey': utxo['scriptPubKey'],
                                    'confirmations': confirmations
                                })
                    return utxos
            else:
                # For legacy wallets, use listunspent
                result = self._safe_rpc_call('listunspent', [min_confirmations, 9999999, [address]])
                if result:
                    return result
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting unspent outputs for {address}: {e}")
            return []
    
    def create_raw_transaction(self, inputs, outputs):
        """Create a raw transaction"""
        try:
            result = self._safe_rpc_call('createrawtransaction', [inputs, outputs])
            if result:
                self.transaction_created.emit(result)
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error creating raw transaction: {e}")
            error_msg = f"Transaction creation failed: {str(e)}"
            self.transaction_error.emit(error_msg)
            return None
    
    def sign_raw_transaction(self, raw_tx, private_keys=None):
        """Sign a raw transaction"""
        try:
            if private_keys:
                result = self._safe_rpc_call('signrawtransactionwithkey', [raw_tx, private_keys])
            else:
                result = self._safe_rpc_call('signrawtransactionwithwallet', [raw_tx])
            
            if result and result.get('complete', False):
                signed_tx = result['hex']
                self.transaction_signed.emit(signed_tx)
                return signed_tx
            else:
                errors = result.get('errors', []) if result else []
                error_msg = f"Transaction signing failed: {errors}"
                self.transaction_error.emit(error_msg)
                return None
                
        except Exception as e:
            logger.error(f"Error signing raw transaction: {e}")
            error_msg = f"Transaction signing failed: {str(e)}"
            self.transaction_error.emit(error_msg)
            return None
    
    def broadcast_transaction(self, signed_tx):
        """Broadcast a signed transaction"""
        try:
            result = self._safe_rpc_call('sendrawtransaction', [signed_tx])
            if result:
                self.transaction_broadcasted.emit(result)
                return result
            return None
            
        except Exception as e:
            logger.error(f"Error broadcasting transaction: {e}")
            error_msg = f"Transaction broadcast failed: {str(e)}"
            self.transaction_error.emit(error_msg)
            return None
    
    def create_and_send_transaction(self, to_address, amount, fee_rate=None, from_address=None):
        """Create, sign, and broadcast a transaction"""
        try:
            # Convert amount to Decimal for precise calculation
            amount = Decimal(str(amount))
            
            # Get UTXOs
            if from_address:
                utxos = self.get_unspent_outputs(from_address)
            else:
                # Use wallet's UTXOs
                utxos = self._safe_rpc_call('listunspent', [1])
            
            if not utxos:
                error_msg = "No unspent outputs available"
                self.transaction_error.emit(error_msg)
                return None
            
            # Calculate total available
            total_available = sum(Decimal(str(utxo['amount'])) for utxo in utxos)
            
            # Estimate fee
            if not fee_rate:
                fee_info = self.estimate_fee()
                if fee_info:
                    fee_rate = fee_info['feerate']
                else:
                    fee_rate = 0.00001  # Default 1 sat/byte
            
            # Select UTXOs (simple algorithm - use all for now)
            inputs = []
            total_input = Decimal('0')
            
            for utxo in utxos:
                inputs.append({
                    'txid': utxo['txid'],
                    'vout': utxo['vout']
                })
                total_input += Decimal(str(utxo['amount']))
                
                # Estimate transaction size (rough)
                tx_size = len(inputs) * 148 + 34 + 10  # inputs + output + overhead
                estimated_fee = Decimal(str(fee_rate)) * Decimal(str(tx_size)) / Decimal('1000')
                
                if total_input >= amount + estimated_fee:
                    break
            
            # Final fee calculation
            tx_size = len(inputs) * 148 + 34 + 10
            fee = Decimal(str(fee_rate)) * Decimal(str(tx_size)) / Decimal('1000')
            
            # Check if we have enough funds
            if total_input < amount + fee:
                error_msg = f"Insufficient funds. Available: {total_input}, Required: {amount + fee}"
                self.transaction_error.emit(error_msg)
                return None
            
            # Create outputs
            outputs = {to_address: float(amount)}
            
            # Add change output if needed
            change = total_input - amount - fee
            if change > Decimal('0.00000546'):  # Dust threshold
                # Get a change address
                change_address = self._safe_rpc_call('getrawchangeaddress')
                if change_address:
                    outputs[change_address] = float(change)
            
            # Create transaction
            raw_tx = self.create_raw_transaction(inputs, outputs)
            if not raw_tx:
                return None
            
            # Sign transaction
            signed_tx = self.sign_raw_transaction(raw_tx)
            if not signed_tx:
                return None
            
            # Broadcast transaction
            tx_id = self.broadcast_transaction(signed_tx)
            return tx_id
            
        except Exception as e:
            logger.error(f"Error creating and sending transaction: {e}")
            error_msg = f"Transaction failed: {str(e)}"
            self.transaction_error.emit(error_msg)
            return None
    
    def _detect_wallet_type(self):
        """Detect if using descriptor wallet or legacy wallet."""
        try:
            # Try to get wallet info
            wallet_info = self._safe_rpc_call('getwalletinfo')
            if wallet_info and 'descriptors' in wallet_info:
                self.is_descriptor_wallet = wallet_info['descriptors']
                print(f"🔍 Wallet type: {'Descriptor' if self.is_descriptor_wallet else 'Legacy'}")
            else:
                # Fallback: try importing a test address to detect wallet type
                try:
                    self.rpc_connection.importaddress("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "", False)
                    self.is_descriptor_wallet = False
                    print("🔍 Wallet type: Legacy (detected via import test)")
                except JSONRPCException as e:
                    if "descriptor wallet" in str(e).lower():
                        self.is_descriptor_wallet = True
                        print("🔍 Wallet type: Descriptor (detected via import error)")
                    else:
                        self.is_descriptor_wallet = False
                        print("🔍 Wallet type: Legacy (default)")
        except Exception as e:
            print(f"⚠️ Could not detect wallet type: {e}")
            self.is_descriptor_wallet = False
