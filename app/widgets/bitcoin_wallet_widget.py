from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont
from decimal import Decimal


class BitcoinWalletWidget(QWidget):
    """Widget to display Bitcoin wallet information synced with the blockchain."""
    
    def __init__(self, address=None):
        super().__init__()
        self.address = address
        self.balance = Decimal('0')
        self.transactions = []
        self.init_ui()
        
    def init_ui(self):
        """Initialize the wallet widget UI."""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Wallet info group
        wallet_group = QGroupBox("Bitcoin Wallet Status")
        wallet_layout = QVBoxLayout()
        wallet_group.setLayout(wallet_layout)
        
        # Address display
        address_layout = QHBoxLayout()
        address_layout.addWidget(QLabel("Address:"))
        self.address_label = QLabel(self.address or "No address loaded")
        self.address_label.setStyleSheet("font-family: monospace; color: #333;")
        self.address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        address_layout.addWidget(self.address_label)
        wallet_layout.addLayout(address_layout)
        
        # Balance display
        balance_layout = QHBoxLayout()
        balance_layout.addWidget(QLabel("Balance:"))
        self.balance_label = QLabel("0.00000000 BTC")
        self.balance_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32;")
        balance_layout.addWidget(self.balance_label)
        balance_layout.addStretch()
        wallet_layout.addLayout(balance_layout)
        
        # USD value
        self.balance_usd_label = QLabel("≈ $0.00 USD")
        self.balance_usd_label.setStyleSheet("color: #666; font-style: italic;")
        wallet_layout.addWidget(self.balance_usd_label)
        
        # Sync status
        sync_layout = QHBoxLayout()
        sync_layout.addWidget(QLabel("Sync Status:"))
        self.sync_status_label = QLabel("⚫ Not connected")
        self.sync_status_label.setStyleSheet("color: #666;")
        sync_layout.addWidget(self.sync_status_label)
        sync_layout.addStretch()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.request_balance_update)
        sync_layout.addWidget(self.refresh_button)
        
        wallet_layout.addLayout(sync_layout)
        
        layout.addWidget(wallet_group)
        
        # Recent transactions
        tx_group = QGroupBox("Recent Transactions")
        tx_layout = QVBoxLayout()
        tx_group.setLayout(tx_layout)
        
        self.transaction_list = QListWidget()
        self.transaction_list.setMaximumHeight(200)
        tx_layout.addWidget(self.transaction_list)
        
        layout.addWidget(tx_group)
        
        # Add transaction placeholder
        self.add_placeholder_transaction()
        
    def set_address(self, address):
        """Set the Bitcoin address for this wallet."""
        self.address = address
        self.address_label.setText(address)
        
    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        """Update the connection status display."""
        if connected:
            self.sync_status_label.setText("🟢 Connected")
            self.sync_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.sync_status_label.setText("⚫ Not connected")
            self.sync_status_label.setStyleSheet("color: red;")
    
    @pyqtSlot(dict)
    def update_balance_from_blockchain(self, balance_info):
        """Update balance from blockchain data."""
        if not self.address:
            return
            
        # In a real implementation, this would filter balance_info for this specific address
        # For now, we'll show a placeholder
        self.balance = Decimal('0.00000000')
        self.balance_label.setText(f"{self.balance:.8f} BTC")
        self.balance_usd_label.setText("≈ $0.00 USD")
        
        # Update sync status
        self.sync_status_label.setText("🔄 Syncing...")
        
    def update_balance(self, balance_btc, balance_usd=None):
        """Manually update balance (for testing or external updates)."""
        self.balance = Decimal(str(balance_btc))
        self.balance_label.setText(f"{self.balance:.8f} BTC")
        
        if balance_usd is not None:
            self.balance_usd_label.setText(f"≈ ${balance_usd:.2f} USD")
            
    def add_transaction(self, tx_data):
        """Add a transaction to the recent transactions list."""
        tx_type = "📤 Sent" if tx_data.get('type') == 'sent' else "📥 Received"
        amount = tx_data.get('amount', 0)
        timestamp = tx_data.get('timestamp', 'Unknown')
        
        item_text = f"{tx_type} {amount:.8f} BTC - {timestamp}"
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, tx_data)
        
        self.transaction_list.insertItem(0, item)
        
        # Keep only last 10 transactions
        while self.transaction_list.count() > 10:
            self.transaction_list.takeItem(self.transaction_list.count() - 1)
    
    def add_placeholder_transaction(self):
        """Add placeholder transaction for demo."""
        placeholder_tx = {
            'type': 'received',
            'amount': 0.00100000,
            'timestamp': 'Demo transaction',
            'txid': 'demo_tx_1'
        }
        self.add_transaction(placeholder_tx)
        
    def request_balance_update(self):
        """Request a balance update from the Bitcoin service."""
        # This will be connected to the Bitcoin service in the main window
        self.sync_status_label.setText("🔄 Updating...")
        self.sync_status_label.setStyleSheet("color: blue; font-style: italic;")
        
    def get_balance(self):
        """Get current balance as Decimal."""
        return self.balance
        
    def get_address(self):
        """Get the current address."""
        return self.address
