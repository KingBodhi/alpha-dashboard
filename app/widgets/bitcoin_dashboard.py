from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QGroupBox,
                             QGridLayout, QProgressBar, QTextEdit, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont, QPalette
import json
from datetime import datetime
from app.config.bitcoin_config import UI_CONFIG


class BitcoinDashboard(QWidget):
    """Main Bitcoin dashboard widget displaying blockchain status and data."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Connection status
        self.create_connection_status(layout)
        
        # Create tabs for different sections
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Blockchain info tab
        self.blockchain_tab = self.create_blockchain_tab()
        tabs.addTab(self.blockchain_tab, "Blockchain")
        
        # Network info tab
        self.network_tab = self.create_network_tab()
        tabs.addTab(self.network_tab, "Network")
        
        # Recent blocks tab
        self.blocks_tab = self.create_blocks_tab()
        tabs.addTab(self.blocks_tab, "Recent Blocks")
        
        # Peers tab
        self.peers_tab = self.create_peers_tab()
        tabs.addTab(self.peers_tab, "Peers")
        
    def create_connection_status(self, parent_layout):
        """Create connection status indicator."""
        status_group = QGroupBox("Bitcoin Node Connection")
        status_layout = QHBoxLayout()
        status_group.setLayout(status_layout)
        
        self.connection_label = QLabel("⚫ Disconnected")
        self.connection_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
        status_layout.addWidget(self.connection_label)
        
        status_layout.addStretch()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.on_connect_clicked)
        status_layout.addWidget(self.connect_button)
        
        self.config_button = QPushButton("Settings")
        self.config_button.clicked.connect(self.on_config_clicked)
        status_layout.addWidget(self.config_button)
        
        parent_layout.addWidget(status_group)
        
    def create_blockchain_tab(self):
        """Create blockchain information tab."""
        widget = QWidget()
        layout = QGridLayout()
        widget.setLayout(layout)
        
        # Blockchain stats
        layout.addWidget(QLabel("Chain:"), 0, 0)
        self.chain_label = QLabel("Unknown")
        layout.addWidget(self.chain_label, 0, 1)
        
        layout.addWidget(QLabel("Blocks:"), 1, 0)
        self.blocks_label = QLabel("0")
        layout.addWidget(self.blocks_label, 1, 1)
        
        layout.addWidget(QLabel("Headers:"), 2, 0)
        self.headers_label = QLabel("0")
        layout.addWidget(self.headers_label, 2, 1)
        
        layout.addWidget(QLabel("Best Block Hash:"), 3, 0)
        self.best_hash_label = QLabel("None")
        self.best_hash_label.setWordWrap(True)
        self.best_hash_label.setStyleSheet("QLabel { font-family: monospace; }")
        layout.addWidget(self.best_hash_label, 3, 1)
        
        layout.addWidget(QLabel("Difficulty:"), 4, 0)
        self.difficulty_label = QLabel("0")
        layout.addWidget(self.difficulty_label, 4, 1)
        
        layout.addWidget(QLabel("Verification Progress:"), 5, 0)
        self.verification_progress = QProgressBar()
        self.verification_progress.setRange(0, 100)
        layout.addWidget(self.verification_progress, 5, 1)
        
        layout.addWidget(QLabel("Size on Disk:"), 6, 0)
        self.size_label = QLabel("0 MB")
        layout.addWidget(self.size_label, 6, 1)
        
        # Add stretch to push content to top
        layout.setRowStretch(7, 1)
        
        return widget
        
    def create_network_tab(self):
        """Create network information tab."""
        widget = QWidget()
        layout = QGridLayout()
        widget.setLayout(layout)
        
        layout.addWidget(QLabel("Version:"), 0, 0)
        self.version_label = QLabel("Unknown")
        layout.addWidget(self.version_label, 0, 1)
        
        layout.addWidget(QLabel("Protocol Version:"), 1, 0)
        self.protocol_label = QLabel("0")
        layout.addWidget(self.protocol_label, 1, 1)
        
        layout.addWidget(QLabel("Connections:"), 2, 0)
        self.connections_label = QLabel("0")
        layout.addWidget(self.connections_label, 2, 1)
        
        layout.addWidget(QLabel("Network Active:"), 3, 0)
        self.network_active_label = QLabel("Unknown")
        layout.addWidget(self.network_active_label, 3, 1)
        
        layout.addWidget(QLabel("Mempool Size:"), 4, 0)
        self.mempool_size_label = QLabel("0 transactions")
        layout.addWidget(self.mempool_size_label, 4, 1)
        
        layout.addWidget(QLabel("Mempool Bytes:"), 5, 0)
        self.mempool_bytes_label = QLabel("0 bytes")
        layout.addWidget(self.mempool_bytes_label, 5, 1)
        
        layout.setRowStretch(6, 1)
        
        return widget
        
    def create_blocks_tab(self):
        """Create recent blocks tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        layout.addWidget(QLabel("Recent Blocks:"))
        
        self.blocks_list = QListWidget()
        self.blocks_list.itemDoubleClicked.connect(self.on_block_double_clicked)
        layout.addWidget(self.blocks_list)
        
        return widget
        
    def create_peers_tab(self):
        """Create peers information tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        layout.addWidget(QLabel("Connected Peers:"))
        
        self.peers_list = QListWidget()
        layout.addWidget(self.peers_list)
        
        return widget
    
    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        """Update connection status display."""
        if connected:
            self.connection_label.setText("🟢 Connected")
            self.connection_label.setStyleSheet("QLabel { color: green; font-weight: bold; }")
            self.connect_button.setText("Disconnect")
        else:
            self.connection_label.setText("⚫ Disconnected")
            self.connection_label.setStyleSheet("QLabel { color: red; font-weight: bold; }")
            self.connect_button.setText("Connect")
    
    @pyqtSlot(dict)
    def update_blockchain_info(self, info):
        """Update blockchain information display."""
        self.chain_label.setText(info.get('chain', 'Unknown'))
        self.blocks_label.setText(f"{info.get('blocks', 0):,}")
        self.headers_label.setText(f"{info.get('headers', 0):,}")
        self.best_hash_label.setText(info.get('bestblockhash', 'None'))
        
        difficulty = info.get('difficulty', 0)
        if difficulty > 1e12:
            difficulty_str = f"{difficulty/1e12:.2f}T"
        elif difficulty > 1e9:
            difficulty_str = f"{difficulty/1e9:.2f}B"
        elif difficulty > 1e6:
            difficulty_str = f"{difficulty/1e6:.2f}M"
        else:
            difficulty_str = f"{difficulty:,.0f}"
        self.difficulty_label.setText(difficulty_str)
        
        verification_progress = info.get('verificationprogress', 0) * 100
        self.verification_progress.setValue(int(verification_progress))
        
        size_on_disk = info.get('size_on_disk', 0)
        if size_on_disk > 1e9:
            size_str = f"{size_on_disk/1e9:.2f} GB"
        elif size_on_disk > 1e6:
            size_str = f"{size_on_disk/1e6:.2f} MB"
        else:
            size_str = f"{size_on_disk:,} bytes"
        self.size_label.setText(size_str)
    
    @pyqtSlot(dict)
    def update_network_info(self, info):
        """Update network information display."""
        self.version_label.setText(str(info.get('version', 'Unknown')))
        self.protocol_label.setText(str(info.get('protocolversion', 0)))
        self.connections_label.setText(str(info.get('connections', 0)))
        self.network_active_label.setText("Yes" if info.get('networkactive', False) else "No")
    
    @pyqtSlot(dict)
    def update_mempool_info(self, info):
        """Update mempool information display."""
        size = info.get('size', 0)
        self.mempool_size_label.setText(f"{size:,} transactions")
        
        bytes_size = info.get('bytes', 0)
        if bytes_size > 1e6:
            bytes_str = f"{bytes_size/1e6:.2f} MB"
        elif bytes_size > 1e3:
            bytes_str = f"{bytes_size/1e3:.2f} KB"
        else:
            bytes_str = f"{bytes_size} bytes"
        self.mempool_bytes_label.setText(bytes_str)
    
    @pyqtSlot(dict)
    def add_new_block(self, block_data):
        """Add a new block to the recent blocks list."""
        height = block_data.get('height', 'Unknown')
        block_hash = block_data.get('hash', 'Unknown')
        timestamp = block_data.get('time', 0)
        tx_count = len(block_data.get('tx', []))
        
        # Format timestamp
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = 'Unknown'
        
        # Create list item
        item_text = f"Block #{height} - {time_str} - {tx_count} txs"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, block_data)
        
        # Add to top of list
        self.blocks_list.insertItem(0, item)
        
        # Keep only configured number of recent blocks
        while self.blocks_list.count() > UI_CONFIG["max_recent_blocks"]:
            self.blocks_list.takeItem(self.blocks_list.count() - 1)
    
    @pyqtSlot(list)
    def update_peers_info(self, peers):
        """Update peers information display."""
        self.peers_list.clear()
        
        for peer in peers:
            addr = peer.get('addr', 'Unknown')
            version = peer.get('version', 0)
            subver = peer.get('subver', 'Unknown')
            conntime = peer.get('conntime', 0)
            
            # Format connection time
            if conntime:
                dt = datetime.fromtimestamp(conntime)
                conn_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                conn_time_str = 'Unknown'
            
            item_text = f"{addr} - {subver} (v{version}) - Connected: {conn_time_str}"
            self.peers_list.addItem(item_text)
    
    def on_connect_clicked(self):
        """Handle connect/disconnect button click."""
        # This will be connected to the service in the main window
        pass
    
    def on_config_clicked(self):
        """Handle settings button click."""
        from app.widgets.bitcoin_config_dialog import BitcoinConfigDialog
        
        dialog = BitcoinConfigDialog(self)
        dialog.settings_changed.connect(self.on_settings_changed)
        dialog.exec()
    
    def on_settings_changed(self, settings):
        """Handle settings change from config dialog."""
        # This will be connected in the main window
        pass
    
    def on_block_double_clicked(self, item):
        """Handle double-click on block item."""
        block_data = item.data(Qt.ItemDataRole.UserRole)
        if block_data:
            # Create a popup window with detailed block information
            self.show_block_details(block_data)
    
    def show_block_details(self, block_data):
        """Show detailed block information in a popup."""
        from PyQt6.QtWidgets import QDialog, QTextEdit, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Block Details - {block_data.get('hash', 'Unknown')[:16]}...")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(json.dumps(block_data, indent=2))
        layout.addWidget(text_edit)
        
        dialog.exec()
