import json
import threading
import time
import platform
import os
import logging
from datetime import datetime
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
    address_performance_status = pyqtSignal(str, str)  # address, status_message
    
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
        
        # Fallback mode using block explorer APIs
        self.use_api_fallback = False
        self.api_endpoints = {
            'blockstream': 'https://blockstream.info/api',
            'blockchain_info': 'https://blockchain.info',
            'mempool_space': 'https://mempool.space/api'
        }
        self.current_api = 'blockstream'  # Default to Blockstream API
        
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
        """Establish connection to Bitcoin node with adaptive retry logic and no-node fallback."""
        # Check if we should even try to connect
        if hasattr(self, '_no_node_mode') and self._no_node_mode:
            print("📍 Running in no-node mode - Bitcoin Core not available")
            self.is_connected = False
            self.connection_status_changed.emit(False)
            self.status_message.emit("📍 No Bitcoin Core - Address monitoring only")
            return False
        
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
                
                # Reset no-node mode if we successfully connect
                if hasattr(self, '_no_node_mode'):
                    self._no_node_mode = False
                
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
                
                # Detect wallet type first
                self._detect_wallet_type()
                
                # Ensure a wallet is loaded for transaction operations
                wallet_loaded = self.ensure_wallet_loaded()
                if not wallet_loaded:
                    print("⚠️ Warning: No wallet loaded - transaction features will be limited")
                
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
        
        # All attempts failed - enable no-node mode
        print("❌ All connection attempts failed - enabling no-node mode")
        self._no_node_mode = True
        self.is_connected = False
        self.connection_status_changed.emit(False)
        self.status_message.emit("📍 No Bitcoin Core found - Address monitoring disabled")
        self.error_occurred.emit("No Bitcoin Core node found. Install Bitcoin Core or connect to a remote node for full functionality.")
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
                # If connection failed, check if we're in no-node mode
                if hasattr(self, '_no_node_mode') and self._no_node_mode:
                    print("📍 Starting in no-node mode - address display only")
                    # Still emit some basic info for UI
                    mock_blockchain_info = {
                        'chain': 'main',
                        'blocks': 0,
                        'headers': 0,
                        'verificationprogress': 0.0,
                        'bestblockhash': '',
                        'difficulty': 0,
                        'chainwork': '0'
                    }
                    self.blockchain_info_updated.emit(mock_blockchain_info)
                    return True  # Return True so dashboard still starts
                return False
        
        # Start periodic updates (only if connected)
        if self.is_connected:
            self.update_timer.start()
            
            # Start background monitoring thread
            self.should_stop = False
            self.worker_thread = threading.Thread(target=self._monitor_blocks, daemon=True)
            self.worker_thread.start()
            
            print("🔍 Started monitoring Bitcoin node")
        else:
            print("📍 Started in no-node mode")
            
        return True
    
    def update_data(self):
        """Update various Bitcoin node data with adaptive error handling for busy nodes."""
        # Skip updates if in no-node mode
        if hasattr(self, '_no_node_mode') and self._no_node_mode:
            return
            
        if not self.is_connected or not self.rpc_connection:
            return
        
        # Skip updates if we have too many consecutive connection failures
        if hasattr(self, '_rpc_failure_count') and self._rpc_failure_count > 25:
            # Only disconnect after many more failures and emit warning instead
            self.status_message.emit("⚠️ Node extremely busy - minimal updates only")
            # Don't disconnect, just use minimal mode
            if self._rpc_failure_count > 50:  # Much higher threshold for actual disconnect
                self.is_connected = False
                self.connection_status_changed.emit(False)
                self.status_message.emit("❌ Connection lost - too many failures")
                print(f"🔌 Disconnecting due to {self._rpc_failure_count} consecutive failures")
                return
        
        try:
            # For very busy nodes, only try the most essential call
            if getattr(self, 'node_busy', False) and getattr(self, '_rpc_failure_count', 0) > 10:
                # Ultra-minimal mode for extremely busy nodes
                print("⏳ Node extremely busy - using minimal mode")
                blockchain_info = self._safe_rpc_call(self.rpc_connection.getblockchaininfo, timeout_override=60, max_retries=1)
                if blockchain_info:
                    self.last_blockchain_info = blockchain_info
                    self.blockchain_info_updated.emit(blockchain_info)
                    self.status_message.emit("⏳ Node very busy - minimal updates only")
                else:
                    self.status_message.emit("❌ Node too busy - waiting...")
                return
            
            # Always try to get blockchain info first
            blockchain_info = self._safe_rpc_call(self.rpc_connection.getblockchaininfo, timeout_override=45, max_retries=2)
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
                self.status_message.emit("⚠️ Bitcoin Core is very busy - reducing update frequency")
                return
            
            # Only get other info if node is not busy and we're not in failure mode
            if not self.node_busy and getattr(self, '_rpc_failure_count', 0) < 5:
                # Reduce load by alternating between different types of info
                update_cycle = getattr(self, '_update_cycle', 0)
                self._update_cycle = (update_cycle + 1) % 4
                
                if update_cycle == 0:
                    # Cycle 0: Network info
                    network_info = self._safe_rpc_call(self.rpc_connection.getnetworkinfo, max_retries=1)
                    if network_info:
                        self.network_info_updated.emit(network_info)
                elif update_cycle == 1:
                    # Cycle 1: Mempool info
                    mempool_info = self._safe_rpc_call(self.rpc_connection.getmempoolinfo, max_retries=1)
                    if mempool_info:
                        self.mempool_updated.emit(mempool_info)
                elif update_cycle == 2:
                    # Cycle 2: Peer info (reduced count)
                    peer_info = self._safe_rpc_call(
                        lambda: self.rpc_connection.getpeerinfo()[:5],  # Reduced from max_peers_display
                        max_retries=1
                    )
                    if peer_info:
                        self.peer_info_updated.emit(peer_info)
                elif update_cycle == 3:
                    # Cycle 3: Address updates (only if we have monitored addresses)
                    if self.monitored_addresses:
                        self.update_all_monitored_addresses()
            
        except Exception as e:
            self._handle_update_error(e)
    
    def _safe_rpc_call(self, rpc_func_or_method, params=None, timeout_override=None, max_retries=3):
        """Make RPC call with aggressive timeout and retry handling for busy nodes."""
        timeout = timeout_override or self.base_timeout
        
        for attempt in range(max_retries):
            try:
                # Increase timeout for each retry
                current_timeout = timeout * (attempt + 1)
                
                # Update connection timeout if needed
                if hasattr(self.rpc_connection, '_timeout'):
                    self.rpc_connection._timeout = current_timeout
                
                start_time = time.time()
                
                # Handle both callable functions and method names with parameters
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
                
                # Track slow calls and adjust timeouts
                if call_time > self.slow_call_threshold:
                    self.base_timeout = min(120, self.base_timeout * 1.1)
                    if attempt == 0:  # Only log on first attempt
                        print(f"⚠️ Slow RPC call: {call_time:.1f}s (adjusting timeout to {self.base_timeout:.1f}s)")
                
                # Success - reset any failure counters
                if hasattr(self, '_rpc_failure_count'):
                    self._rpc_failure_count = 0
                
                return result
                
            except JSONRPCException as e:
                error_msg = str(e)
                
                # Handle wallet loading
                if "no wallet is loaded" in error_msg.lower():
                    if attempt == 0:  # Only try once per call
                        print("⚠️ RPC call failed: No wallet loaded")
                        if self.ensure_wallet_loaded():
                            print("🔄 Retrying RPC call after loading wallet...")
                            continue
                    return None
                
                # Handle busy node errors with retries
                elif any(x in error_msg.lower() for x in ["request-sent", "work queue", "timeout", "busy", "loading block index"]):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Progressive backoff: 2s, 4s, 6s
                        # Only log the first busy error per RPC call to reduce noise
                        if attempt == 0 and not hasattr(self, '_last_busy_error_time'):
                            print(f"⏳ Node busy (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                            self._last_busy_error_time = time.time()
                        elif attempt == 0 and hasattr(self, '_last_busy_error_time'):
                            # Only print if it's been more than 60 seconds since last busy error message
                            if time.time() - self._last_busy_error_time > 60:
                                print(f"⏳ Node busy (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                self._last_busy_error_time = time.time()
                        time.sleep(wait_time)
                        continue
                    else:
                        # All retries failed
                        self.node_busy = True
                        if not hasattr(self, '_rpc_failure_count'):
                            self._rpc_failure_count = 0
                        self._rpc_failure_count += 1
                        
                        # Only log every 10th failure to avoid spam (increased from 5)
                        if self._rpc_failure_count % 10 == 1:
                            print(f"⚠️ Bitcoin node consistently busy - call failed after {max_retries} attempts (failure count: {self._rpc_failure_count})")
                        return None
                
                # Other errors
                else:
                    if attempt == 0:  # Only log unexpected errors once
                        print(f"RPC Error: {e.error.get('message', error_msg) if hasattr(e, 'error') else error_msg}")
                    return None
                    
            except Exception as e:
                error_str = str(e).lower()
                # Handle connection/timeout errors with retries
                if any(x in error_str for x in ["timeout", "connection", "request-sent", "socket", "network"]):
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3  # Longer wait for connection issues
                        # Only print on first attempt and throttle messages to reduce spam
                        if attempt == 0 and not hasattr(self, '_last_connection_error_time'):
                            print(f"🔌 Connection issue (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                            self._last_connection_error_time = time.time()
                        elif attempt == 0 and hasattr(self, '_last_connection_error_time'):
                            # Only print if it's been more than 2 minutes since last error message
                            if time.time() - self._last_connection_error_time > 120:
                                print(f"🔌 Connection issue (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                                self._last_connection_error_time = time.time()
                        time.sleep(wait_time)
                        continue
                    else:
                        # Connection completely failed - increment failure counter
                        if not hasattr(self, '_rpc_failure_count'):
                            self._rpc_failure_count = 0
                        self._rpc_failure_count += 1
                        
                        # Only log connection failures occasionally to avoid spam
                        if self._rpc_failure_count % 10 == 1:
                            print(f"🔌 Connection issues (failure count: {self._rpc_failure_count})")
                        return None
                else:
                    # Unexpected error
                    if attempt == 0:
                        print(f"RPC call failed: {error_str}")
                    return None
        
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
            
            # Try to import the address for better transaction detection (only for legacy wallets)
            if self.is_connected and not self.is_descriptor_wallet:
                try:
                    # Try to import address for transaction tracking (legacy wallets only)
                    import_result = self._safe_rpc_call(lambda: self.rpc_connection.importaddress(address, f"monitor_{address[:8]}", False))
                    if import_result is not None:
                        print(f"✅ Address {address[:8]}... imported for transaction tracking")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"⚠️ Could not import address {address[:8]}...: {e}")
            elif self.is_connected and self.is_descriptor_wallet:
                print(f"📍 Descriptor wallet - monitoring {address[:8]}... without import")
                
                # Update balance and transactions immediately
                self.update_address_balance(address)
                self.update_address_transactions(address)
    
    def remove_address_from_monitor(self, address):
        """Remove a Bitcoin address from monitoring."""
        if address in self.monitored_addresses:
            self.monitored_addresses.remove(address)
            self.address_balances.pop(address, None)
            self.address_transactions.pop(address, None)
            print(f"📍 Stopped monitoring address: {address}")
    
    def update_address_balance(self, address):
        """Update balance for a specific address in a dedicated worker thread."""
        def worker():
            try:
                # Original logic moved here
                if hasattr(self, '_no_node_mode') and self._no_node_mode:
                    if not hasattr(self, '_no_node_message_shown'):
                        print(f"📍 No-node mode: Cannot check balance for {address[:8]}... - Bitcoin Core required")
                        self._no_node_message_shown = True
                    balance_info = {
                        'balance_btc': Decimal('0'),
                        'balance_usd': 0.0,
                        'confirmed': Decimal('0'),
                        'unconfirmed': Decimal('0'),
                        'utxo_count': 0,
                        'last_updated': time.time(),
                        'error': 'No Bitcoin Core node available'
                    }
                    self.address_balance_updated.emit(address, balance_info)
                    return

                if not self.is_connected or not self.rpc_connection:
                    return

                if getattr(self, '_rpc_failure_count', 0) > 25:
                    print(f"⏳ Skipping balance update for {address[:8]}... - node too busy")
                    return

                balance_btc = Decimal('0')
                utxo_count = 0

                try:
                    print(f"📊 Checking balance for {address[:8]}... (threaded)")
                    start_time = time.time()
                    scan_result = self._safe_rpc_call(
                        lambda: self.rpc_connection.scantxoutset("start", [f"addr({address})"]),
                        timeout_override=120,
                        max_retries=1
                    )
                    elapsed_time = time.time() - start_time
                    if scan_result:
                        balance_btc = Decimal(str(scan_result.get('total_amount', 0)))
                        utxo_count = len(scan_result.get('unspents', []))
                        if elapsed_time > 20:
                            if not hasattr(self, '_slow_scan_addresses'):
                                self._slow_scan_addresses = {}
                            self._slow_scan_addresses[address] = time.time()
                            print(f"⚠️ SLOW scantxoutset: {elapsed_time:.1f}s - will reduce frequency for this address")
                            self.address_performance_status.emit(address, f"⏱️ Slow node - updates every 15min")
                        print(f"📊 Balance check complete: {balance_btc:.8f} BTC ({utxo_count} UTXOs) in {elapsed_time:.1f}s")
                    else:
                        print(f"⏳ Balance check timed out for {address[:8]}... after {elapsed_time:.1f}s")
                        if not hasattr(self, '_slow_scan_addresses'):
                            self._slow_scan_addresses = {}
                        self._slow_scan_addresses[address] = time.time()
                        self.address_performance_status.emit(address, f"⏱️ Slow node - updates every 15min")
                        return
                except Exception as e:
                    error_str = str(e).lower()
                    if any(phrase in error_str for phrase in ['busy', 'request-sent', 'timeout', 'loading block index', 'verifying']):
                        print(f"⏳ Balance check failed - node busy, will retry later for {address[:8]}...")
                        return
                    else:
                        print(f"⚠️ Balance check error for {address[:8]}...: {e}")
                        balance_btc = Decimal('0')

                old_balance = self.address_balances.get(address, Decimal('0'))
                self.address_balances[address] = balance_btc
                btc_price_usd = self.get_btc_price_estimate()
                balance_usd = float(balance_btc) * btc_price_usd
                balance_info = {
                    'balance_btc': balance_btc,
                    'balance_usd': balance_usd,
                    'confirmed': balance_btc,
                    'unconfirmed': Decimal('0'),
                    'utxo_count': utxo_count,
                    'last_updated': time.time()
                }
                self.address_balance_updated.emit(address, balance_info)
                if balance_btc > 0:
                    print(f"💰 Balance: {balance_btc:.8f} BTC (${balance_usd:.2f}) for {address[:8]}...")
                    self.status_message.emit(f"✅ Balance: {balance_btc:.8f} BTC")
                    if balance_btc > old_balance:
                        print(f"📈 Balance increased - will update transactions in next cycle")
                        if not hasattr(self, '_pending_tx_updates'):
                            self._pending_tx_updates = set()
                        self._pending_tx_updates.add(address)
                else:
                    if not hasattr(self, '_zero_balance_shown'):
                        self.status_message.emit(f"📍 Monitoring address - No funds detected")
                        self._zero_balance_shown = True
            except Exception as e:
                print(f"❌ Error updating balance for {address}: {e}")
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
        threading.Thread(target=worker, daemon=True).start()
    
    def get_btc_price_estimate(self):
        """Get Bitcoin price estimate (placeholder - would use real API)."""
        # This is a placeholder. In a real implementation, you'd fetch from an API
        return 45000.0  # Example BTC price in USD
    
    def update_address_transactions(self, address):
        """Update transaction history for a specific address in a dedicated worker thread."""
        def worker():
            try:
                if not self.is_connected or not self.rpc_connection:
                    return
                transactions = []
                try:
                    wallet_txs = self._safe_rpc_call(lambda: self.rpc_connection.listtransactions("*", 1000))
                    if wallet_txs:
                        for tx in wallet_txs:
                            if tx.get('address') == address:
                                formatted_tx = {
                                    'txid': tx.get('txid', ''),
                                    'amount': abs(float(tx.get('amount', 0))),
                                    'fee': abs(float(tx.get('fee', 0))) if tx.get('fee') else 0,
                                    'confirmations': tx.get('confirmations', 0),
                                    'time': tx.get('time', int(time.time())),
                                    'timestamp': datetime.fromtimestamp(tx.get('time', int(time.time()))).isoformat(),
                                    'type': 'receive' if tx.get('amount', 0) > 0 else 'send',
                                    'address': address,
                                    'category': tx.get('category', ''),
                                    'blockhash': tx.get('blockhash', ''),
                                    'blockindex': tx.get('blockindex', 0),
                                    'blocktime': tx.get('blocktime', 0),
                                    'status': 'confirmed' if tx.get('confirmations', 0) >= 6 else 'pending'
                                }
                                transactions.append(formatted_tx)
                        print(f"📋 Found {len(transactions)} wallet transactions for {address[:8]}...")
                except Exception as wallet_error:
                    print(f"⚠️ Could not get wallet transactions: {wallet_error}")
                    try:
                        best_block_hash = self._safe_rpc_call(lambda: self.rpc_connection.getbestblockhash())
                        if best_block_hash:
                            print(f"🔍 Scanning recent blocks for transactions to {address[:8]}...")
                            current_hash = best_block_hash
                            blocks_scanned = 0
                            for i in range(50):
                                if not current_hash:
                                    break
                                block = self._safe_rpc_call(lambda: self.rpc_connection.getblock(current_hash, 2))
                                if block and 'tx' in block:
                                    blocks_scanned += 1
                                    for tx in block['tx']:
                                        tx_involves_address = False
                                        tx_amount = 0
                                        tx_type = 'unknown'
                                        for vout in tx.get('vout', []):
                                            script_pub_key = vout.get('scriptPubKey', {})
                                            addresses_in_output = script_pub_key.get('addresses', [])
                                            if 'address' in script_pub_key:
                                                addresses_in_output.append(script_pub_key['address'])
                                            if address in addresses_in_output:
                                                tx_involves_address = True
                                                tx_amount += vout.get('value', 0)
                                                tx_type = 'receive'
                                        for vin in tx.get('vin', []):
                                            if 'txid' in vin and 'vout' in vin:
                                                prev_tx = self._safe_rpc_call(lambda: self.rpc_connection.getrawtransaction(vin['txid'], True))
                                                if prev_tx and 'vout' in prev_tx:
                                                    prev_output = prev_tx['vout'][vin['vout']]
                                                    prev_addresses = prev_output.get('scriptPubKey', {}).get('addresses', [])
                                                    if address in prev_addresses:
                                                        tx_involves_address = True
                                                        tx_amount = prev_output.get('value', 0)
                                                        tx_type = 'send'
                                        if tx_involves_address:
                                            current_height = self.last_blockchain_info.get('blocks', 0)
                                            block_height = block.get('height', 0)
                                            confirmations = max(0, current_height - block_height + 1)
                                            formatted_tx = {
                                                'txid': tx.get('txid', ''),
                                                'amount': tx_amount,
                                                'fee': 0,
                                                'confirmations': confirmations,
                                                'time': block.get('time', int(time.time())),
                                                'timestamp': datetime.fromtimestamp(block.get('time', int(time.time()))).isoformat(),
                                                'type': tx_type,
                                                'address': address,
                                                'blockhash': block.get('hash', ''),
                                                'blockindex': block.get('height', 0),
                                                'blocktime': block.get('time', 0),
                                                'status': 'confirmed' if confirmations >= 6 else 'pending'
                                            }
                                            transactions.append(formatted_tx)
                                            print(f"🔍 Found {tx_type} transaction: {tx['txid'][:16]}... ({tx_amount:.8f} BTC)")
                                    current_hash = block.get('previousblockhash')
                            print(f"📋 Scanned {blocks_scanned} blocks, found {len(transactions)} blockchain transactions for {address[:8]}...")
                    except Exception as block_error:
                        print(f"⚠️ Could not scan blockchain: {block_error}")
                if address not in self.address_transactions:
                    self.address_transactions[address] = []
                existing_txids = {tx.get('txid') for tx in self.address_transactions[address]}
                new_transactions = [tx for tx in transactions if tx.get('txid') not in existing_txids]
                if new_transactions:
                    self.address_transactions[address].extend(new_transactions)
                    print(f"📋 Added {len(new_transactions)} new transactions for {address[:8]}...")
                self.address_transactions[address].sort(key=lambda x: x.get('time', 0), reverse=True)
                self.address_transactions_updated.emit(address, self.address_transactions[address])
            except Exception as e:
                print(f"❌ Error updating transactions for {address}: {e}")
                self.address_transactions_updated.emit(address, [])
        threading.Thread(target=worker, daemon=True).start()
    
    def update_all_monitored_addresses(self):
        """Update all monitored addresses in a dedicated worker thread."""
        def worker():
            try:
                if not self.monitored_addresses:
                    return
                if getattr(self, '_rpc_failure_count', 0) > 10:
                    if not hasattr(self, '_busy_skip_counter'):
                        self._busy_skip_counter = 0
                    self._busy_skip_counter += 1
                    if self._busy_skip_counter < 10:
                        print(f"⏳ Skipping address updates - node too busy ({self._busy_skip_counter}/10)")
                        return
                    self._busy_skip_counter = 0
                    print(f"🔄 Attempting address updates on very busy node...")
                if self.node_busy:
                    if not hasattr(self, '_skip_address_update_counter'):
                        self._skip_address_update_counter = 0
                    self._skip_address_update_counter += 1
                    if self._skip_address_update_counter < 5:
                        print(f"⏳ Skipping address updates while node is busy ({self._skip_address_update_counter}/5)")
                        return
                    self._skip_address_update_counter = 0
                    print(f"🔄 Retrying address updates after busy period")
                if not hasattr(self, '_address_update_rotation'):
                    self._address_update_rotation = 0
                address_list = list(self.monitored_addresses)
                if address_list:
                    current_address = address_list[self._address_update_rotation % len(address_list)]
                    self._address_update_rotation += 1
                    slow_addresses = getattr(self, '_slow_scan_addresses', {})
                    if current_address in slow_addresses:
                        time_since_last = time.time() - slow_addresses[current_address]
                        if time_since_last < 900:
                            print(f"⏳ Skipping slow address {current_address[:8]}... (waiting {900-time_since_last:.0f}s)")
                            self.address_performance_status.emit(current_address, f"⏳ Throttled - next check in {int((900-time_since_last)/60)}min")
                            return
                        else:
                            print(f"� Updating slow address {current_address[:8]}... (last update was {time_since_last/60:.1f} minutes ago)")
                    print(f"�📍 Updating address {self._address_update_rotation}/{len(address_list)}: {current_address[:8]}...")
                    self.update_address_balance(current_address)
                    if hasattr(self, '_pending_tx_updates') and self._pending_tx_updates:
                        if current_address in self._pending_tx_updates:
                            print(f"📋 Processing pending transaction update for {current_address[:8]}...")
                            self.update_address_transactions(current_address)
                            self._pending_tx_updates.discard(current_address)
                    elif current_address not in slow_addresses and self._address_update_rotation % (len(address_list) * 5) == 0:
                        print(f"📋 Periodic transaction update for {current_address[:8]}...")
                        self.update_address_transactions(current_address)
            except Exception as e:
                print(f"❌ Error updating all monitored addresses: {e}")
        threading.Thread(target=worker, daemon=True).start()
    
    def _adjust_update_frequency(self, success=True):
        """Dynamically adjust update frequency based on node responsiveness with aggressive scaling for busy nodes."""
        current_interval = self.update_timer.interval()
        
        if success:
            # Gradually return to normal frequency if things are working well
            if current_interval > self.update_interval:
                # But be very conservative about speeding up
                new_interval = max(self.update_interval, current_interval - 5000)  # Only reduce by 5s at a time
                self.update_timer.setInterval(new_interval)
                if new_interval != current_interval:
                    print(f"📈 Update frequency slightly increased to {new_interval/1000}s")
        else:
            # Aggressively slow down updates when having issues
            failure_count = getattr(self, '_rpc_failure_count', 0)
            
            if failure_count > 20:
                # Extremely busy - 5 minute intervals
                new_interval = 300000  # 5 minutes
            elif failure_count > 10:
                # Very busy - 2 minute intervals
                new_interval = 120000  # 2 minutes
            elif failure_count > 5:
                # Busy - 1 minute intervals
                new_interval = 60000   # 1 minute
            else:
                # Somewhat busy - progressive increase
                max_interval = 120000 if self.is_low_power_device else 60000  # 2min or 1min max normally
                new_interval = min(max_interval, current_interval + 10000)  # Increase by 10s
            
            if new_interval != current_interval:
                self.update_timer.setInterval(new_interval)
                print(f"📉 Update frequency reduced to {new_interval/1000}s due to node being busy (failures: {failure_count})")
    
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
        """Estimate transaction fee for confirmation in target blocks in a worker thread."""
        def worker():
            if not self.is_connected:
                print("❌ Not connected to Bitcoin node")
                return None
            try:
                if not self.ensure_wallet_loaded():
                    print("⚠️ Using fallback fee estimation (no wallet loaded)")
                    fallback_fee_data = {
                        'feerate': 0.00001000,
                        'blocks': target_blocks,
                        'errors': ['Using fallback fee - no wallet loaded']
                    }
                    self.fee_estimated.emit(fallback_fee_data)
                    return fallback_fee_data
                result = self._safe_rpc_call(lambda: self.rpc_connection.estimatesmartfee(target_blocks))
                if result and 'feerate' in result:
                    fee_data = {
                        'feerate': result['feerate'],
                        'blocks': target_blocks,
                        'errors': result.get('errors', [])
                    }
                    self.fee_estimated.emit(fee_data)
                    return fee_data
                result = self._safe_rpc_call(lambda: self.rpc_connection.estimatefee(target_blocks))
                if result and result > 0:
                    fee_data = {
                        'feerate': result,
                        'blocks': target_blocks,
                        'errors': []
                    }
                    self.fee_estimated.emit(fee_data)
                    return fee_data
                fee_data = {
                    'feerate': 0.00001,
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
        threading.Thread(target=worker, daemon=True).start()
    
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
        """Sign a raw transaction in a worker thread."""
        def worker():
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
        threading.Thread(target=worker, daemon=True).start()
    
    def broadcast_transaction(self, signed_tx):
        """Broadcast a signed transaction in a worker thread."""
        def worker():
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
        threading.Thread(target=worker, daemon=True).start()
    
    def create_and_send_transaction(self, to_address, amount, fee_rate=None, from_address=None):
        """Create, sign, and broadcast a transaction in a dedicated worker thread."""
        def worker():
            try:
                amount_dec = Decimal(str(amount))
                if from_address:
                    utxos = self.get_unspent_outputs(from_address)
                else:
                    utxos = self._safe_rpc_call('listunspent', [1])
                if not utxos:
                    error_msg = "No unspent outputs available"
                    self.transaction_error.emit(error_msg)
                    return None
                total_available = sum(Decimal(str(utxo['amount'])) for utxo in utxos)
                if not fee_rate:
                    fee_info = self.estimate_fee()
                    if fee_info:
                        fee_rate = fee_info['feerate']
                    else:
                        fee_rate = 0.00001
                inputs = []
                total_input = Decimal('0')
                for utxo in utxos:
                    inputs.append({
                        'txid': utxo['txid'],
                        'vout': utxo['vout']
                    })
                    total_input += Decimal(str(utxo['amount']))
                    tx_size = len(inputs) * 148 + 34 + 10
                    estimated_fee = Decimal(str(fee_rate)) * Decimal(str(tx_size)) / Decimal('1000')
                    if total_input >= amount_dec + estimated_fee:
                        break
                tx_size = len(inputs) * 148 + 34 + 10
                fee = Decimal(str(fee_rate)) * Decimal(str(tx_size)) / Decimal('1000')
                if total_input < amount_dec + fee:
                    error_msg = f"Insufficient funds. Available: {total_input}, Required: {amount_dec + fee}"
                    self.transaction_error.emit(error_msg)
                    return None
                outputs = {to_address: float(amount_dec)}
                change = total_input - amount_dec - fee
                if change > Decimal('0.00000546'):
                    change_address = self._safe_rpc_call('getrawchangeaddress')
                    if change_address:
                        outputs[change_address] = float(change)
                raw_tx = self.create_raw_transaction(inputs, outputs)
                if not raw_tx:
                    return None
                signed_tx = self.sign_raw_transaction(raw_tx)
                if not signed_tx:
                    return None
                tx_id = self.broadcast_transaction(signed_tx)
                return tx_id
            except Exception as e:
                logger.error(f"Error creating and sending transaction: {e}")
                error_msg = f"Transaction failed: {str(e)}"
                self.transaction_error.emit(error_msg)
                return None
        threading.Thread(target=worker, daemon=True).start()
    
    def _detect_wallet_type(self):
        """Detect if using descriptor wallet or legacy wallet."""
        try:
            # Try to get wallet info first
            wallet_info = self._safe_rpc_call(lambda: self.rpc_connection.getwalletinfo())
            if wallet_info and 'descriptors' in wallet_info:
                self.is_descriptor_wallet = wallet_info['descriptors']
                print(f"🔍 Wallet type: {'Descriptor' if self.is_descriptor_wallet else 'Legacy'}")
                return
            
            # If no wallet loaded, try to detect by testing a command
            try:
                # Test with a harmless importaddress call to detect wallet type
                test_result = self._safe_rpc_call(
                    lambda: self.rpc_connection.importaddress("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "", False, False),
                    max_retries=1
                )
                if test_result is not None:
                    self.is_descriptor_wallet = False
                    print("🔍 Wallet type: Legacy (detected via import test)")
                else:
                    # Import failed, might be descriptor wallet
                    self.is_descriptor_wallet = True
                    print("🔍 Wallet type: Descriptor (import failed - likely descriptor)")
            except Exception as e:
                error_str = str(e).lower()
                if any(phrase in error_str for phrase in ["descriptor wallet", "only legacy", "descriptors"]):
                    self.is_descriptor_wallet = True
                    print("🔍 Wallet type: Descriptor (detected via import error)")
                elif "no wallet" in error_str:
                    # No wallet loaded - assume descriptor for safety
                    self.is_descriptor_wallet = True
                    print("🔍 Wallet type: Descriptor (no wallet loaded - assuming descriptor)")
                else:
                    self.is_descriptor_wallet = False
                    print("🔍 Wallet type: Legacy (default)")
                    
        except Exception as e:
            print(f"⚠️ Could not detect wallet type: {e}")
            # Default to descriptor wallet for modern Bitcoin Core compatibility
            self.is_descriptor_wallet = True
            print("🔍 Wallet type: Descriptor (default for safety)")
    
    def ensure_wallet_loaded(self):
        """Ensure a wallet is loaded for transaction operations."""
        try:
            # Try to get wallet info to check if a wallet is loaded
            wallet_info = self._safe_rpc_call(lambda: self.rpc_connection.getwalletinfo())
            if wallet_info:
                print(f"✅ Wallet loaded: {wallet_info.get('walletname', 'default')}")
                return True
        except Exception as e:
            error_str = str(e).lower()
            if "no wallet is loaded" in error_str:
                print("📝 No wallet loaded, attempting to create/load wallet...")
                
                # Try to list existing wallets first
                try:
                    wallet_list = self._safe_rpc_call(lambda: self.rpc_connection.listwalletdir())
                    if wallet_list and wallet_list.get('wallets'):
                        # Load the first available wallet
                        first_wallet = wallet_list['wallets'][0]['name']
                        load_result = self._safe_rpc_call(lambda: self.rpc_connection.loadwallet(first_wallet))
                        if load_result:
                            print(f"✅ Loaded existing wallet: {first_wallet}")
                            return True
                except Exception as load_error:
                    print(f"⚠️ Could not load existing wallet: {load_error}")
                
                # Create a new wallet if no existing wallet can be loaded
                try:
                    # Create a descriptor wallet (modern Bitcoin Core)
                    # Parameters: wallet_name, disable_private_keys, blank, passphrase, avoid_reuse, descriptors, load_on_startup
                    create_result = self._safe_rpc_call(
                        lambda: self.rpc_connection.createwallet("dashboard_wallet", False, False, "", False, True, True)
                    )
                    if create_result:
                        print("✅ Created new dashboard wallet")
                        return True
                except Exception as create_error:
                    create_error_str = str(create_error).lower()
                    if "already exists" in create_error_str:
                        # Wallet exists but wasn't loaded, try to load it
                        try:
                            load_result = self._safe_rpc_call(lambda: self.rpc_connection.loadwallet("dashboard_wallet"))
                            if load_result:
                                print("✅ Loaded existing dashboard wallet")
                                return True
                        except Exception as load_error2:
                            print(f"❌ Could not load existing dashboard wallet: {load_error2}")
                    else:
                        print(f"❌ Could not create wallet: {create_error}")
            else:
                print(f"❌ Wallet check failed: {e}")
        
        return False
    
    # =====================================================================
    # DESCRIPTOR WALLET FUNCTIONALITY
    # =====================================================================
    
    def get_wallet_descriptors(self):
        """Get all descriptors from the loaded wallet."""
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
            # Get descriptors (only works for descriptor wallets)
            descriptors = self._safe_rpc_call(
                lambda: self.rpc_connection.listdescriptors()
            )
            
            if descriptors:
                logger.info(f"Retrieved {len(descriptors.get('descriptors', []))} wallet descriptors")
                return descriptors
            else:
                logger.warning("Could not retrieve wallet descriptors - may not be a descriptor wallet")
                return None
                
        except Exception as e:
            logger.warning(f"Error getting descriptors (wallet may not support them): {e}")
            return None
    
    def generate_wallet_address(self, address_type='bech32', label=None):
        """
        Generate a new address from the wallet.
        
        Args:
            address_type: 'legacy', 'p2sh-segwit', or 'bech32'
            label: Optional label for the address
            
        Returns:
            New address string
        """
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
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
                address = self._safe_rpc_call(
                    lambda: self.rpc_connection.getnewaddress(label, core_type)
                )
            else:
                address = self._safe_rpc_call(
                    lambda: self.rpc_connection.getnewaddress("", core_type)
                )
            
            if address:
                logger.info(f"Generated new {address_type} address: {address[:16]}...")
                return address
            else:
                logger.error(f"Failed to generate {address_type} address")
                return None
                
        except Exception as e:
            logger.error(f"Error generating new address: {e}")
            return None
    
    def get_wallet_addresses(self, include_change=False):
        """
        Get all addresses from the wallet.
        
        Args:
            include_change: Whether to include change addresses
            
        Returns:
            List of addresses with their information
        """
        if not self.is_connected or not self.rpc_connection:
            return []
            
        try:
            addresses = []
            
            # Get receiving addresses
            receiving_addresses = self._safe_rpc_call(
                lambda: self.rpc_connection.getaddressesbylabel("")
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
                    change_address = self._safe_rpc_call(
                        lambda: self.rpc_connection.getrawchangeaddress()
                    )
                    if change_address:
                        addr_info = self.get_address_info(change_address)
                        addresses.append({
                            'address': change_address,
                            'type': self._detect_address_type(change_address),
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
        if not self.is_connected or not self.rpc_connection:
            return None
            
        try:
            # Get address info from Bitcoin Core
            addr_info = self._safe_rpc_call(
                lambda: self.rpc_connection.getaddressinfo(address)
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
    
    def get_all_wallet_address_types(self):
        """
        Get addresses of all types from the wallet, generating if needed.
        
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
                addresses['bech32'] = self.generate_wallet_address('bech32', 'Dashboard Native SegWit')
            if not addresses['p2sh_segwit']:
                addresses['p2sh_segwit'] = self.generate_wallet_address('p2sh-segwit', 'Dashboard P2SH SegWit')
            if not addresses['legacy']:
                addresses['legacy'] = self.generate_wallet_address('legacy', 'Dashboard Legacy')
            
            return addresses
            
        except Exception as e:
            logger.error(f"Error getting all address types: {e}")
            return {}
    
    def validate_address_ownership(self, address):
        """
        Validate that an address belongs to the loaded wallet.
        
        Args:
            address: Address to validate
            
        Returns:
            True if address belongs to wallet, False otherwise
        """
        try:
            addr_info = self.get_address_info(address)
            if addr_info:
                return addr_info.get('ismine', False)
            
            return False
            
        except Exception as e:
            logger.warning(f"Error validating address ownership: {e}")
            return False
