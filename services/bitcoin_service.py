import json
import threading
import time
from decimal import Decimal
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG, UI_CONFIG


class BitcoinService(QObject):
    """Service to handle Bitcoin RPC connections and data updates."""
    
    # Signals for UI updates
    connection_status_changed = pyqtSignal(bool)  # True if connected, False if disconnected
    blockchain_info_updated = pyqtSignal(dict)   # Latest blockchain info
    new_block_received = pyqtSignal(dict)        # New block data
    mempool_updated = pyqtSignal(dict)           # Mempool statistics
    network_info_updated = pyqtSignal(dict)     # Network information
    peer_info_updated = pyqtSignal(list)        # Connected peers
    error_occurred = pyqtSignal(str)            # Error messages
    
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
        
        # Update timers
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_data)
        self.update_timer.setInterval(BITCOIN_RPC_CONFIG["update_interval"])  # Use config interval
        
        # Background thread for blocking operations
        self.worker_thread = None
        self.should_stop = False
        
    def connect_to_node(self):
        """Establish connection to Bitcoin node."""
        try:
            rpc_url = f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}"
            self.rpc_connection = AuthServiceProxy(rpc_url)
            
            # Test connection with a simple call
            info = self.rpc_connection.getblockchaininfo()
            
            self.is_connected = True
            self.connection_status_changed.emit(True)
            
            print(f"✅ Connected to Bitcoin node at {self.rpc_host}:{self.rpc_port}")
            print(f"📊 Chain: {info.get('chain', 'unknown')}")
            print(f"📦 Blocks: {info.get('blocks', 0)}")
            
            return True
            
        except JSONRPCException as e:
            error_msg = f"RPC Error: {e.error['message']}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
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
        """Update various Bitcoin node data."""
        if not self.is_connected or not self.rpc_connection:
            return
        
        try:
            # Get blockchain info
            blockchain_info = self.rpc_connection.getblockchaininfo()
            self.blockchain_info_updated.emit(blockchain_info)
            
            # Get network info
            network_info = self.rpc_connection.getnetworkinfo()
            self.network_info_updated.emit(network_info)
            
            # Get mempool info
            mempool_info = self.rpc_connection.getmempoolinfo()
            self.mempool_updated.emit(mempool_info)
            
            # Get peer info (limit to prevent UI overload)
            peer_info = self.rpc_connection.getpeerinfo()[:UI_CONFIG["max_peers_display"]]
            self.peer_info_updated.emit(peer_info)
            
        except JSONRPCException as e:
            error_msg = f"RPC Error during update: {e.error['message']}"
            print(f"❌ {error_msg}")
            self.error_occurred.emit(error_msg)
            
        except Exception as e:
            error_msg = f"Update failed: {str(e)}"
            print(f"❌ {error_msg}")
            # Don't emit error for Decimal conversion issues, just log them
            if "Decimal" not in str(e):
                self.error_occurred.emit(error_msg)
            # Try to reconnect on next update
            self.is_connected = False
    
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
