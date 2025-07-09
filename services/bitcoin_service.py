import json
import threading
import time
import platform
import os
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
        
        # Adaptive settings based on system capabilities
        self.is_low_power_device = self._detect_low_power_device()
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
        self.node_busy = False
        
        # Adaptive timeouts based on device type
        if self.is_low_power_device:
            self.base_timeout = 45
            self.connection_timeout = 60
            self.update_interval = 20000  # 20 seconds
            self.max_retries = 8
            self.retry_delay = 5
            print("🔧 Low-power device detected - using extended timeouts")
        else:
            self.base_timeout = 15
            self.connection_timeout = 30
            self.update_interval = BITCOIN_RPC_CONFIG["update_interval"]
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
            # Check if it's a Raspberry Pi
            if os.path.exists('/proc/cpuinfo'):
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                    if 'raspberry pi' in cpuinfo or 'bcm' in cpuinfo:
                        return True
            
            # Check ARM architecture (common on low-power devices)
            machine = platform.machine().lower()
            if 'arm' in machine or 'aarch64' in machine:
                return True
            
            # Check available memory if psutil is available
            if HAS_PSUTIL:
                memory_gb = psutil.virtual_memory().total / (1024**3)
                if memory_gb < 4:  # Less than 4GB RAM
                    return True
            
            return False
            
        except Exception:
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
                self.blockchain_info_updated.emit(blockchain_info)
                self.consecutive_failures = 0
                
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
    
    def _safe_rpc_call(self, rpc_func, timeout_override=None):
        """Make RPC call with timeout and error handling."""
        try:
            timeout = timeout_override or self.base_timeout
            
            # Create a new connection for this call with specific timeout
            rpc_url = f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}"
            temp_rpc = AuthServiceProxy(rpc_url, timeout=timeout)
            
            start_time = time.time()
            result = rpc_func() if hasattr(rpc_func, '__call__') else temp_rpc.__getattr__(rpc_func)()
            call_time = time.time() - start_time
            
            # Track slow calls
            if call_time > self.slow_call_threshold:
                print(f"⚠️ Slow RPC call: {call_time:.1f}s")
            
            return result
            
        except JSONRPCException as e:
            print(f"RPC Error: {e}")
            return None
        except Exception as e:
            if "timeout" in str(e).lower():
                print(f"RPC timeout after {timeout}s")
                return None
            else:
                raise e
    
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
                current_hash = self.rpc_connection.getbestblockhash()
                
                # Check if we have a new block
                if self.last_block_hash and current_hash != self.last_block_hash:
                    # Get block details
                    block_data = self.rpc_connection.getblock(current_hash)
                    self.new_block_received.emit(block_data)
                    print(f"🔗 New block: {current_hash[:16]}... (Height: {block_data.get('height', 'unknown')})")
                
                self.last_block_hash = current_hash
                
                # Sleep for a bit before checking again
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Block monitoring error: {e}")
                time.sleep(5)  # Wait longer on error
    
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
            # Import address to wallet for monitoring (if not already imported)
            try:
                self.rpc_connection.importaddress(address, "", False)
            except JSONRPCException as e:
                # Address might already be imported or node might not support this
                if "already exists" not in str(e).lower():
                    print(f"⚠️ Could not import address {address}: {e}")
            
            # Get address balance using listunspent
            unspent = self._safe_rpc_call(lambda: self.rpc_connection.listunspent(0, 9999999, [address]))
            
            if unspent is not None:
                # Calculate total balance
                balance = sum(Decimal(str(utxo['amount'])) for utxo in unspent)
                self.address_balances[address] = balance
                
                # Get current Bitcoin price for USD conversion (placeholder)
                btc_price_usd = self.get_btc_price_estimate()
                balance_usd = float(balance) * btc_price_usd
                
                balance_info = {
                    'balance_btc': balance,
                    'balance_usd': balance_usd,
                    'confirmed': balance,  # For now, treat all as confirmed
                    'unconfirmed': Decimal('0'),
                    'utxo_count': len(unspent),
                    'last_updated': time.time()
                }
                
                # Emit signal with balance update
                self.address_balance_updated.emit(address, balance_info)
                print(f"💰 Balance updated for {address}: {balance:.8f} BTC")
                
        except Exception as e:
            print(f"❌ Error updating balance for {address}: {e}")
    
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
