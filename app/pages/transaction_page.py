import sys
print("Python executable:", sys.executable)
try:
    import bitcointx
    print("bitcointx import: SUCCESS")
except Exception as e:
    print("bitcointx import: FAILED", e)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QSplitter, QTabWidget, QScrollArea,
    QMessageBox, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor
import json
from datetime import datetime
from decimal import Decimal


class TransactionPage(QWidget):
    """Bitcoin transaction creation and management page."""
    
    # Signal emitted when a transaction is created (for future blockchain integration)
    transaction_created = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.transaction_history = []
        self.bitcoin_service = None
        self.wallet_address = None
        self.wallet_balance = Decimal('0')
        self.wallet_addresses = {}
        self.wallet_loaded = False
        self.init_ui()
        
    def set_bitcoin_service(self, bitcoin_service):
        """Set the Bitcoin service for blockchain integration."""
        self.bitcoin_service = bitcoin_service
        if self.bitcoin_service:
            # Use queued connections to prevent blocking
            from PyQt6.QtCore import Qt
            
            # Connect to balance updates
            self.bitcoin_service.address_balance_updated.connect(
                self.update_wallet_balance, Qt.ConnectionType.QueuedConnection)
            # Connect to transaction updates  
            self.bitcoin_service.address_transactions_updated.connect(
                self.update_transaction_history_from_blockchain, Qt.ConnectionType.QueuedConnection)
            # Connect to transaction creation signals
            self.bitcoin_service.transaction_created.connect(
                self.on_transaction_created, Qt.ConnectionType.QueuedConnection)
            self.bitcoin_service.transaction_broadcasted.connect(
                self.on_transaction_broadcast, Qt.ConnectionType.QueuedConnection)
            self.bitcoin_service.transaction_error.connect(
                self.on_transaction_error, Qt.ConnectionType.QueuedConnection)
    def create_psbt_base64(self, tx, utxos):
        """
        Create a PSBT from a CTransaction and a list of UTXOs, returning base64-encoded PSBT.
        """
        try:
            from bitcointx.core.psbt import PartiallySignedBitcoinTransaction
            psbt = PartiallySignedBitcoinTransaction()
            psbt.set_unsigned_tx(tx)

            for i, txin in enumerate(tx.vin):
                # Find the matching UTXO for this input
                utxo = next(
                    (
                        u
                        for u in utxos
                        if u.get("txid") == txin.prevout.hash[::-1].hex()
                        and u.get("vout") == txin.prevout.n
                    ),
                    None,
                )
                if utxo is None:
                    raise ValueError(
                        f"UTXO not found for input {i}: txid={txin.prevout.hash[::-1].hex()}, vout={txin.prevout.n}"
                    )
                psbt.add_input(i, utxo=utxo)

            return psbt.to_base64()
        except Exception as e:
            self.logger.error(f"Failed to create PSBT: {e}")
            return ""
    
    def set_bitcoin_core_wallet_addresses(self, wallet_addresses):
        """Set wallet addresses from Bitcoin Core wallet."""
        self.wallet_addresses = wallet_addresses
        self.wallet_loaded = True
        
        # Use bech32 as primary address
        if 'bech32' in wallet_addresses and wallet_addresses['bech32']:
            self.wallet_address = wallet_addresses['bech32']
        elif 'p2sh_segwit' in wallet_addresses and wallet_addresses['p2sh_segwit']:
            self.wallet_address = wallet_addresses['p2sh_segwit']
        elif 'legacy' in wallet_addresses and wallet_addresses['legacy']:
            self.wallet_address = wallet_addresses['legacy']
        
        if self.wallet_address:
            # Update the receive address display if it exists
            if hasattr(self, 'receive_address_label'):
                self.receive_address_label.setText(self.wallet_address)
            print(f"📍 Transaction page using Bitcoin Core wallet address: {self.wallet_address[:8]}...")
            
            # Start monitoring this address
            if self.bitcoin_service:
                self.bitcoin_service.add_address_to_monitor(self.wallet_address)
    
    def set_wallet_address(self, address, private_key_wif=None):
        """Legacy method - now redirects to Bitcoin Core wallet if available."""
        if self.wallet_loaded and self.wallet_addresses:
            # Use Bitcoin Core wallet addresses instead
            print("⚠️ Using Bitcoin Core wallet addresses instead of standalone address")
            return
            
        # Fallback for compatibility (should not be used with Bitcoin Core integration)
        self.wallet_address = address
        self.private_key_wif = private_key_wif
        self._pending_address = address
        
        if address:
            if hasattr(self, 'receive_address_label'):
                self.receive_address_label.setText(address)
            print(f"📍 Transaction page using standalone address: {address[:8]}...")
    
    def on_bitcoin_core_connected(self, wallet_addresses=None):
        """Called when Bitcoin Core connection is established."""
        try:
            print("🟢 Bitcoin Core connected - setting up transaction wallet integration")
            
            if wallet_addresses:
                self.set_bitcoin_core_wallet_addresses(wallet_addresses)
            elif self.bitcoin_service:
                # Get wallet addresses from the Bitcoin service
                try:
                    from app.utils.bitcoin_wallet_descriptor_generator import BitcoinWalletDescriptorGenerator
                    descriptor_generator = BitcoinWalletDescriptorGenerator(self.bitcoin_service)
                    wallet_addresses = descriptor_generator.get_all_address_types()
                    self.set_bitcoin_core_wallet_addresses(wallet_addresses)
                except Exception as e:
                    print(f"⚠️ Could not get wallet addresses for transaction page: {e}")
            
            print("✅ Transaction page wallet integration ready")
                
        except Exception as e:
            print(f"❌ Error setting up transaction wallet after Bitcoin Core connection: {e}")

    def on_bitcoin_core_disconnected(self):
        """Called when Bitcoin Core connection is lost."""
        print("🔴 Bitcoin Core disconnected - transaction wallet functionality limited")
        self.wallet_loaded = False
        self.wallet_addresses = {}
        # Keep the last known address for display purposes but disable sending
    
    def update_wallet_balance(self, address, balance_info):
        """Update wallet balance from Bitcoin service."""
        if address == self.wallet_address:
            self.wallet_balance = balance_info.get('balance_btc', Decimal('0'))
            # Update balance label if it exists (created in send tab)
            if hasattr(self, 'balance_label'):
                self.balance_label.setText(f"Balance: {self.wallet_balance:.8f} BTC")
            print(f"💰 Updated wallet balance: {self.wallet_balance:.8f} BTC")
    
    def update_transaction_history_from_blockchain(self, address, transactions):
        """Update transaction history from blockchain data."""
        if address == self.wallet_address:
            # Clear existing history and replace with blockchain data
            self.transaction_history.clear()
            
            # Convert blockchain transactions to display format
            for tx in transactions:
                display_tx = {
                    "txid": tx.get('txid', ''),
                    "amount": tx.get('amount', 0),
                    "fee": tx.get('fee', 0),
                    "description": f"{tx.get('type', 'unknown').title()} transaction",
                    "timestamp": tx.get('timestamp', ''),
                    "status": tx.get('status', 'unknown'),
                    "type": tx.get('type', 'unknown'),
                    "confirmations": tx.get('confirmations', 0),
                    "blockhash": tx.get('blockhash', ''),
                    "address": tx.get('address', ''),
                    "category": tx.get('category', '')
                }
                self.transaction_history.append(display_tx)
            
            # Update the display
            self.update_transaction_history_display()
            print(f"📋 Updated transaction history from blockchain: {len(transactions)} transactions")
    
    def init_ui(self):
        """Initialize the transaction page UI with deferred loading."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title = QLabel("Bitcoin Transactions")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        # Create tabs for different transaction functions
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Create tabs with deferred content loading to improve startup speed
        QTimer.singleShot(0, self._create_tabs_deferred)
    
    def _create_tabs_deferred(self):
        """Create tab content in a deferred manner to prevent blocking."""
        # Send transaction tab
        self.send_tab = self.create_send_tab()
        self.tabs.addTab(self.send_tab, "Send Bitcoin")
        
        # Defer creation of other tabs
        QTimer.singleShot(50, self._create_remaining_tabs)
    
    def _create_remaining_tabs(self):
        """Create remaining tabs after initial UI is loaded."""
        # Receive tab
        self.receive_tab = self.create_receive_tab()
        self.tabs.addTab(self.receive_tab, "Receive Bitcoin")
        
        # Transaction history tab
        self.history_tab = self.create_history_tab()
        self.tabs.addTab(self.history_tab, "Transaction History")
        
        # Transaction builder tab (advanced)
        self.builder_tab = self.create_builder_tab()
        self.tabs.addTab(self.builder_tab, "Advanced Builder")
        
        # Apply any pending address/balance updates now that UI is ready
        self._apply_pending_updates()
    
    def _apply_pending_updates(self):
        """Apply any pending updates once UI components are created."""
        # Update receive address if we have a pending address
        if hasattr(self, '_pending_address') and self._pending_address:
            if hasattr(self, 'receive_address_label'):
                self.receive_address_label.setText(self._pending_address)
        
        # Update balance display if we have a current balance
        if self.wallet_balance > 0 and hasattr(self, 'balance_label'):
            self.balance_label.setText(f"Balance: {self.wallet_balance:.8f} BTC")
    
    def create_send_tab(self):
        """Create the send Bitcoin tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Scroll area for the form
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_widget.setLayout(form_layout)
        
        # Balance display
        balance_group = QGroupBox("Account Balance")
        balance_layout = QVBoxLayout()
        balance_group.setLayout(balance_layout)
        
        self.balance_label = QLabel("Balance: 0.00000000 BTC")
        self.balance_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2E7D32;")
        balance_layout.addWidget(self.balance_label)
        
        self.balance_usd_label = QLabel("≈ $0.00 USD")
        self.balance_usd_label.setStyleSheet("color: #666; font-style: italic;")
        balance_layout.addWidget(self.balance_usd_label)
        
        form_layout.addWidget(balance_group)
        
        # Send form
        send_group = QGroupBox("Send Bitcoin")
        send_form = QFormLayout()
        send_group.setLayout(send_form)
        
        # Recipient address
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Enter Bitcoin address or BIP21 URI")
        send_form.addRow("Recipient Address:", self.recipient_input)
        
        # Amount section
        amount_layout = QHBoxLayout()
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setDecimals(8)
        self.amount_input.setMaximum(21000000.0)
        self.amount_input.setSuffix(" BTC")
        amount_layout.addWidget(self.amount_input)
        
        self.amount_usd_label = QLabel("≈ $0.00")
        self.amount_usd_label.setStyleSheet("color: #666; margin-left: 10px;")
        amount_layout.addWidget(self.amount_usd_label)
        
        send_form.addRow("Amount:", amount_layout)
        
        # Fee selection
        fee_layout = QVBoxLayout()
        self.fee_combo = QComboBox()
        self.fee_combo.addItems(["Economy (Low Priority)", "Standard (Normal)", "Priority (Fast)", "Custom"])
        fee_layout.addWidget(self.fee_combo)
        
        self.custom_fee_input = QDoubleSpinBox()
        self.custom_fee_input.setDecimals(0)
        self.custom_fee_input.setMaximum(1000)
        self.custom_fee_input.setSuffix(" sats/vB")
        self.custom_fee_input.setToolTip("Custom fee rate in satoshis per virtual byte (sats/vB)")
        self.custom_fee_input.setVisible(False)
        fee_layout.addWidget(self.custom_fee_input)
        
        self.fee_combo.currentTextChanged.connect(self.on_fee_selection_changed)
        self.custom_fee_input.valueChanged.connect(self.update_transaction_preview)
        self.recipient_input.textChanged.connect(self.update_transaction_preview)
        self.amount_input.valueChanged.connect(self.update_transaction_preview)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional description for your records")
        send_form.addRow("Description:", self.description_input)
        self.description_input.textChanged.connect(self.update_transaction_preview)
        
        send_form.addRow("Fee:", fee_layout)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QFormLayout()
        advanced_group.setLayout(advanced_layout)
        
        self.rbf_checkbox = QCheckBox("Replace-by-Fee (RBF)")
        self.rbf_checkbox.setChecked(True)
        advanced_layout.addRow("Options:", self.rbf_checkbox)
        self.rbf_checkbox.stateChanged.connect(self.update_transaction_preview)
        
        form_layout.addWidget(send_group)
        form_layout.addWidget(advanced_group)
        
        # Transaction preview
        preview_group = QGroupBox("Transaction Preview")
        # Mesh Send Button (only enabled if not connected to node)
        self.mesh_send_button = QPushButton("Send via Mesh Network")
        self.mesh_send_button.setStyleSheet("QPushButton { background-color: #1976D2; color: white; font-weight: bold; }")
        self.mesh_send_button.clicked.connect(self.send_psbt_via_mesh)
        self.mesh_send_button.setVisible(True)  # Always show the mesh send button
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        self.preview_text.setPlainText("Enter transaction details to see preview...")
        preview_layout.addWidget(self.preview_text)
        
        form_layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview Transaction")
        self.preview_button.clicked.connect(self.preview_transaction)
        button_layout.addWidget(self.preview_button)
        
        self.send_button = QPushButton("Send Transaction")
        self.send_button.clicked.connect(self.send_transaction)
        self.send_button.setEnabled(False)
        self.send_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        button_layout.addWidget(self.send_button)
        
        self.clear_button = QPushButton("Clear Form")
        self.clear_button.clicked.connect(self.clear_send_form)
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.mesh_send_button)
                
        form_layout.addLayout(button_layout)
        form_layout.addStretch()
                
        scroll_area.setWidget(form_widget)
        layout.addWidget(scroll_area)
                
        return widget
    
    def create_receive_tab(self):
        """Create the receive Bitcoin tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Address display
        address_group = QGroupBox("Your Bitcoin Address")
        address_layout = QVBoxLayout()
        address_group.setLayout(address_layout)
        
        self.receive_address_label = QLabel("Loading address...")
        self.receive_address_label.setStyleSheet("font-family: monospace; font-size: 14px; padding: 10px; background: #f5f5f5; border: 1px solid #ddd;")
        self.receive_address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        address_layout.addWidget(self.receive_address_label)
        
        # Use pending address if available
        if hasattr(self, '_pending_address') and self._pending_address:
            self.receive_address_label.setText(self._pending_address)
        
        # Copy button
        self.copy_address_button = QPushButton("Copy Address")
        self.copy_address_button.clicked.connect(self.copy_address)
        address_layout.addWidget(self.copy_address_button)
        
        layout.addWidget(address_group)
        
        # QR Code display
        qr_group = QGroupBox("QR Code")
        qr_layout = QVBoxLayout()
        qr_group.setLayout(qr_layout)
        
        self.qr_display = QLabel("QR Code will appear here")
        self.qr_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_display.setStyleSheet("border: 1px solid #ddd; min-height: 200px;")
        qr_layout.addWidget(self.qr_display)
        
        layout.addWidget(qr_group)
        
        # Payment request generator
        request_group = QGroupBox("Payment Request")
        request_layout = QFormLayout()
        request_group.setLayout(request_layout)
        
        self.request_amount_input = QDoubleSpinBox()
        self.request_amount_input.setDecimals(8)
        self.request_amount_input.setMaximum(21000000.0)
        self.request_amount_input.setSuffix(" BTC")
        request_layout.addRow("Amount:", self.request_amount_input)
        
        self.request_label_input = QLineEdit()
        self.request_label_input.setPlaceholderText("Optional label for this request")
        request_layout.addRow("Label:", self.request_label_input)
        
        self.request_message_input = QLineEdit()
        self.request_message_input.setPlaceholderText("Optional message")
        request_layout.addRow("Message:", self.request_message_input)
        
        self.generate_qr_button = QPushButton("Generate Payment QR Code")
        self.generate_qr_button.clicked.connect(self.generate_payment_qr)
        request_layout.addRow("", self.generate_qr_button)
        
        layout.addWidget(request_group)
        layout.addStretch()
        
        return widget
    
    def create_history_tab(self):
        """Create the transaction history tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_transaction_history)
        controls_layout.addWidget(self.refresh_button)
        
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_transaction_history)
        controls_layout.addWidget(self.export_button)
        
        controls_layout.addStretch()
        
        # Filter options
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Transactions", "Sent", "Received", "Pending"])
        controls_layout.addWidget(QLabel("Filter:"))
        controls_layout.addWidget(self.filter_combo)
        
        layout.addLayout(controls_layout)
        
        # Transaction list
        self.transaction_list = QListWidget()
        self.transaction_list.itemDoubleClicked.connect(self.show_transaction_details)
        layout.addWidget(self.transaction_list)
        
        # Load initial transaction history
        self.load_transaction_history()
        
        return widget
    
    def create_builder_tab(self):
        """Create the advanced transaction builder tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        # Raw transaction builder
        raw_group = QGroupBox("Raw Transaction Builder")
        raw_layout = QVBoxLayout()
        raw_group.setLayout(raw_layout)
        
        self.raw_tx_input = QTextEdit()
        self.raw_tx_input.setPlaceholderText("Enter raw transaction hex or build using the form below...")
        raw_layout.addWidget(self.raw_tx_input)
        
        raw_buttons = QHBoxLayout()
        self.decode_button = QPushButton("Decode Transaction")
        self.decode_button.clicked.connect(self.decode_transaction)
        raw_buttons.addWidget(self.decode_button)
        
        self.sign_button = QPushButton("Sign Transaction")
        self.sign_button.clicked.connect(self.sign_transaction)
        raw_buttons.addWidget(self.sign_button)
        
        self.broadcast_button = QPushButton("Broadcast Transaction")
        self.broadcast_button.clicked.connect(self.broadcast_transaction)
        raw_buttons.addWidget(self.broadcast_button)
        
        raw_layout.addLayout(raw_buttons)
        
        layout.addWidget(raw_group)
        
        # UTXO management
        utxo_group = QGroupBox("UTXO Management")
        utxo_layout = QVBoxLayout()
        utxo_group.setLayout(utxo_layout)
        
        self.utxo_list = QListWidget()
        utxo_layout.addWidget(self.utxo_list)
        
        utxo_buttons = QHBoxLayout()
        self.refresh_utxo_button = QPushButton("Refresh UTXOs")
        self.refresh_utxo_button.clicked.connect(self.refresh_utxos)
        utxo_buttons.addWidget(self.refresh_utxo_button)
        
        self.coin_control_button = QPushButton("Coin Control")
        self.coin_control_button.clicked.connect(self.open_coin_control)
        utxo_buttons.addWidget(self.coin_control_button)
        
        utxo_layout.addLayout(utxo_buttons)
        
        layout.addWidget(utxo_group)
        layout.addStretch()
        
        return widget
    
    def on_fee_selection_changed(self, text):
        """Handle fee selection change."""
        self.custom_fee_input.setVisible(text == "Custom")
        self.update_transaction_preview()
    
    def preview_transaction(self):
        """Preview the transaction before sending."""
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        
        fee_mode = self.fee_combo.currentText()
        fee_rate = self.get_selected_fee_rate()  # sats/vB
        # Estimate transaction size (vbytes). Typical single-input, single-output tx is ~200 vbytes.
        estimated_size = 200
        fee_btc = (fee_rate * estimated_size) / 1e8  # Convert sats to BTC

        print(f"[PREVIEW] Fee mode: {fee_mode}, Fee rate: {fee_rate} sats/vB, Estimated size: {estimated_size} vB, Calculated fee: {fee_btc:.8f} BTC, Amount: {amount} BTC")
        
        if not recipient or amount <= 0:
            QMessageBox.warning(self, "Input Error", "Please enter a valid recipient address and amount.")
            return
        
        # Create preview text
        preview = f"""Transaction Preview:
        
        To: {recipient}
        Amount: {amount:.8f} BTC
        Fee: {fee_btc:.8f} BTC
        Total: {amount + fee_btc:.8f} BTC

        Description: {self.description_input.text() or 'None'}
        Replace-by-Fee: {'Yes' if self.rbf_checkbox.isChecked() else 'No'}

        Note: This is a preview only. No transaction has been created yet."""
        
        self.preview_text.setPlainText(preview)
        self.send_button.setEnabled(True)
    
    def get_selected_fee(self):
        """Get the selected fee amount."""
        fee_text = self.fee_combo.currentText()
        if fee_text == "Custom":
            return self.custom_fee_input.value()
        elif fee_text.startswith("Economy"):
            return 0.00001000  # Example low fee
        elif fee_text.startswith("Standard"):
            return 0.00005000  # Example normal fee
        elif fee_text.startswith("Priority"):
            return 0.00010000  # Example high fee
        return 0.00005000  # Default
    
    def send_transaction(self):
        """Send the transaction using Bitcoin Core asynchronously."""
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        description = self.description_input.text().strip()

        if not recipient:
            QMessageBox.warning(self, "Error", "Please enter a recipient address.")
            return

        if amount <= 0:
            QMessageBox.warning(self, "Error", "Please enter a valid amount.")
            return

        if amount > float(self.wallet_balance):
            QMessageBox.warning(self, "Error", f"Insufficient funds. Available: {self.wallet_balance:.8f} BTC")
            return

        if not self.bitcoin_service or not self.bitcoin_service.is_connected:
            QMessageBox.warning(self, "Error", "Not connected to Bitcoin node. Please check your connection.")
            return

        # All wallet checks and transaction creation are now threaded in BitcoinService
        fee_rate = self.get_selected_fee_rate()
        print(f"[UI] Selected fee_rate: {fee_rate} sats/vB (raw, before conversion)")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Confirm Transaction")
        msg.setText(f"Send {amount:.8f} BTC to {recipient}?")
        msg.setDetailedText(f"From: {self.wallet_address}\nTo: {recipient}\nAmount: {amount:.8f} BTC\nFee Rate: {fee_rate} sat/byte\nDescription: {description}")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            self.send_button.setEnabled(False)
            self.send_button.setText("Sending...")
            fee_rate_btc = fee_rate / 100000  # sats/vB to BTC/kvB
            print(f"[UI] Converted fee_rate for backend: {fee_rate_btc} BTC/kvB (correct units)")

            # Call the service method (threaded)
            self.bitcoin_service.create_and_send_transaction(
                to_address=recipient,
                amount=amount,
                fee_rate=fee_rate_btc,
                from_address=self.wallet_address
            )
            # Do NOT expect a return value; UI will update via signals
    
    def get_selected_fee_rate(self):
        """Get the selected fee rate in satoshis per byte."""
        fee_text = self.fee_combo.currentText()
        if fee_text == "Custom":
            return self.custom_fee_input.value()
        elif fee_text.startswith("Economy"):
            return 1  # 1 sat/byte for slow confirmation
        elif fee_text.startswith("Standard"):
            return 5  # 5 sat/byte for normal confirmation
        elif fee_text.startswith("Priority"):
            return 20  # 20 sat/byte for fast confirmation
        return 5  # Default
    
    def on_transaction_created(self, raw_tx_hex):
        """Handle successful transaction creation."""
        print(f"✅ Transaction created: {raw_tx_hex[:20]}...")
    
    def on_transaction_broadcast(self, tx_id):
        """Handle successful transaction broadcast."""
        self.send_button.setEnabled(True)
        self.send_button.setText("Send Bitcoin")
        
        # Add to history
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        description = self.description_input.text().strip()
        
        tx_record = {
            "txid": tx_id,
            "recipient": recipient,
            "amount": float(amount),
            "fee": 0,  # We don't have fee info from the signal
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "status": "broadcast",
            "type": "send"
        }
        self.transaction_history.append(tx_record)
        
        # Show success message
        QMessageBox.information(
            self, 
            "Transaction Sent!", 
            f"Transaction broadcasted successfully!\n\nTransaction ID: {tx_id}\n\nThe transaction is now being processed by the Bitcoin network."
        )
        
        # Clear form
        self.recipient_input.clear()
        self.amount_input.setValue(0)
        self.description_input.clear()
    def send_psbt_via_mesh(self):
        """Create a PSBT and send it via the Meshtastic mesh network with a custom prefix."""
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        fee_rate = self.get_selected_fee_rate()
        from_address = self.wallet_address

        if not recipient or amount <= 0:
            QMessageBox.warning(self, "Input Error", "Please enter a valid recipient address and amount.")
            return

        psbt_base64 = self.create_psbt_base64(recipient, amount, fee_rate, from_address)
        if not psbt_base64:
            return

        try:
            import logging
            from services.meshtastic_service import MeshtasticService
            logger = logging.getLogger("MeshtasticMeshSend")
            custom_prefix = "APN_PSBT:"
            logger.info(f"Attempting to broadcast PSBT via mesh: {custom_prefix}{psbt_base64}")
            success = MeshtasticService.sendText(f"{custom_prefix}{psbt_base64}")
            if success:
                logger.info("Mesh broadcast successful.")
                QMessageBox.information(self, "PSBT Sent", "PSBT has been sent via the mesh network.")
            else:
                logger.error("Mesh broadcast failed.")
                QMessageBox.critical(self, "Mesh Send Error", "Failed to send PSBT via mesh network. Check logs for details.")
        except Exception as e:
            QMessageBox.critical(self, "Mesh Send Error", f"Failed to send PSBT via mesh: {e}")
        
        # Update history display
        self.update_transaction_history_display()
    
    def on_transaction_error(self, error):
        """Handle transaction error and provide user feedback with full context."""
        import traceback
        self.send_button.setEnabled(True)
        self.send_button.setText("Send Bitcoin")
        # Show error message and log full error object and stack trace for diagnostics
        error_message = str(error)
        error_trace = traceback.format_exc()
        QMessageBox.critical(
            self,
            "Transaction Error",
            f"Transaction failed:\n\n{error_message}\n\nStack Trace:\n{error_trace}"
        )
        # Optionally, show a status message or log to a UI status bar
        if hasattr(self, 'balance_label'):
            self.balance_label.setText("Error: Transaction failed")
        print(f"❌ Transaction error: {error_message}\n{error_trace}")
    
    def clear_send_form(self):
        """Clear the send form."""
        self.recipient_input.clear()
        self.amount_input.setValue(0.0)
        self.description_input.clear()
        self.fee_combo.setCurrentIndex(1)  # Standard fee
        self.rbf_checkbox.setChecked(True)
        self.preview_text.setPlainText("Enter transaction details to see preview...")
        self.send_button.setEnabled(False)
    
    def copy_address(self):
        """Copy the receive address to clipboard."""
        from PyQt6.QtGui import QGuiApplication
        address = self.receive_address_label.text()
        QGuiApplication.clipboard().setText(address)
        QMessageBox.information(self, "Copied", f"Address copied to clipboard:\n{address}")
    
    def generate_payment_qr(self):
        """Generate a payment QR code."""
        import qrcode
        from PyQt6.QtGui import QPixmap, QImage
        import io

        address = self.receive_address_label.text().strip()
        if not address or address == "Loading address...":
            QMessageBox.warning(self, "Error", "No Bitcoin address available.")
            return

        # Build Bitcoin URI
        uri = f"bitcoin:{address}"
        params = []
        amount = self.request_amount_input.value()
        if amount > 0:
            params.append(f"amount={amount:.8f}")
        label = self.request_label_input.text().strip()
        if label:
            params.append(f"label={label}")
        message = self.request_message_input.text().strip()
        if message:
            params.append(f"message={message}")
        if params:
            uri += "?" + "&".join(params)

        # Generate QR code
        qr_img = qrcode.make(uri)
        buffer = io.BytesIO()
        qr_img.save(buffer, "PNG")
        qt_image = QImage.fromData(buffer.getvalue())
        pixmap = QPixmap.fromImage(qt_image)
        self.qr_display.setPixmap(pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.qr_display.setText("")  # Remove placeholder text
    
    def load_transaction_history(self):
        """Load transaction history into the list."""
        # Use a timer to defer this operation and prevent blocking
        QTimer.singleShot(0, self._load_transaction_history_deferred)
    
    def _load_transaction_history_deferred(self):
        """Deferred transaction history loading."""
        self.transaction_list.clear()
        
        if not self.transaction_history:
            # Show message if no transactions
            item = QListWidgetItem("No transactions found. Click 'Refresh' to load from blockchain.")
            item.setData(Qt.ItemDataRole.UserRole, None)
            self.transaction_list.addItem(item)
            return
        
        for tx in self.transaction_history:
            # Determine status icon
            confirmations = tx.get("confirmations", 0)
            if confirmations >= 6:
                status_icon = "✅"
                status_text = "Confirmed"
            elif confirmations > 0:
                status_icon = "⏳" 
                status_text = f"{confirmations} conf"
            else:
                status_icon = "❓"
                status_text = "Unconfirmed"
            
            # Determine transaction type icon
            tx_type = tx.get("type", "unknown")
            if tx_type == "receive" or tx.get("category") == "receive":
                type_icon = "�"
                type_text = "Received"
            elif tx_type == "send" or tx.get("category") == "send":
                type_icon = "📤" 
                type_text = "Sent"
            else:
                type_icon = "🔄"
                type_text = "Transaction"
            
            # Format amount
            amount = tx.get('amount', 0)
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except:
                    amount = 0
            
            # Create display text
            txid = tx.get('txid', 'Unknown')[:16] + "..." if tx.get('txid') else "Unknown"
            item_text = f"{status_icon} {type_icon} {type_text}: {amount:.8f} BTC ({status_text}) - {txid}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, tx)
            self.transaction_list.addItem(item)
    
    def refresh_transaction_history(self):
        """Refresh transaction history from the blockchain."""
        if not self.bitcoin_service or not self.bitcoin_service.is_connected:
            QMessageBox.warning(self, "Error", "Not connected to Bitcoin node.")
            return
        
        if not self.wallet_address:
            QMessageBox.warning(self, "Error", "No wallet address available.")
            return
        
        # Show loading state
        self.refresh_button.setText("Refreshing...")
        self.refresh_button.setEnabled(False)
        
        try:
            # Force immediate update of both balance and transactions
            print(f"🔄 Forcing refresh for address: {self.wallet_address}")
            
            # Update balance first (this might detect new UTXOs)
            self.bitcoin_service.update_address_balance(self.wallet_address)
            
            # Then force transaction update
            self.bitcoin_service.update_address_transactions(self.wallet_address)
            
            # Also try to rescan if possible
            try:
                if hasattr(self.bitcoin_service, '_safe_rpc_call'):
                    # Try to rescan the last few blocks
                    current_height = self.bitcoin_service.last_blockchain_info.get('blocks', 0)
                    start_height = max(0, current_height - 100)  # Scan last 100 blocks
                    rescan_result = self.bitcoin_service._safe_rpc_call(
                        lambda: self.bitcoin_service.rpc_connection.rescanblockchain(start_height)
                    )
                    if rescan_result:
                        print(f"🔍 Rescanned blocks {start_height} to {current_height}")
            except Exception as rescan_error:
                print(f"⚠️ Could not rescan: {rescan_error}")
            
            QMessageBox.information(self, "Success", "Transaction history refresh initiated. Please wait a moment for updates to appear.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh transaction history: {e}")
        finally:
            self.refresh_button.setText("Refresh")
            self.refresh_button.setEnabled(True)
    
    def export_transaction_history(self):
        """Export transaction history to CSV."""
        if not self.transaction_history:
            QMessageBox.warning(self, "No Data", "No transactions to export.")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Transaction History", 
            f"bitcoin_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='') as csvfile:
                    fieldnames = ['timestamp', 'type', 'amount', 'fee', 'description', 'status', 'txid']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for tx in self.transaction_history:
                        writer.writerow({
                            'timestamp': tx.get('timestamp', ''),
                            'type': 'sent' if 'recipient' in tx else 'received',
                            'amount': tx.get('amount', 0),
                            'fee': tx.get('fee', 0),
                            'description': tx.get('description', ''),
                            'status': tx.get('status', ''),
                            'txid': tx.get('txid', '')
                        })
                
                QMessageBox.information(self, "Export Complete", f"Transaction history exported to:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export transaction history:\n{str(e)}")
    
    def show_transaction_details(self, item):
        """Show detailed transaction information."""
        tx = item.data(Qt.ItemDataRole.UserRole)
        if tx:
            details = json.dumps(tx, indent=2)
            
            from PyQt6.QtWidgets import QDialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Transaction Details - {tx.get('txid', 'Unknown')}")
            dialog.resize(500, 400)
            
            layout = QVBoxLayout()
            dialog.setLayout(layout)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(details)
            layout.addWidget(text_edit)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.close)
            layout.addWidget(close_button)
            
            dialog.exec()
    
    def update_transaction_preview(self):
        """Update the transaction preview when inputs change."""
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.value()
        fee_mode = self.fee_combo.currentText()
        fee_rate = self.get_selected_fee_rate()  # sats/vB
        estimated_size = 200
        fee_btc = (fee_rate * estimated_size) / 1e8  # Convert sats to BTC

        print(f"[PREVIEW][AUTO] Fee mode: {fee_mode}, Fee rate: {fee_rate} sats/vB, Estimated size: {estimated_size} vB, Calculated fee: {fee_btc:.8f} BTC, Amount: {amount} BTC")

        if not recipient or amount <= 0:
            self.preview_text.setPlainText("Enter transaction details to see preview...")
            self.send_button.setEnabled(False)
            return

        preview = f"""Transaction Preview:

        To: {recipient}
        Amount: {amount:.8f} BTC
        Fee: {fee_btc:.8f} BTC
        Total: {amount + fee_btc:.8f} BTC

        Description: {self.description_input.text() or 'None'}
        Replace-by-Fee: {'Yes' if self.rbf_checkbox.isChecked() else 'No'}

        Note: This is a preview only. No transaction has been created yet."""
        self.preview_text.setPlainText(preview)
        self.send_button.setEnabled(True)
    
    def decode_transaction(self):
        """Decode a raw transaction."""
        raw_tx = self.raw_tx_input.toPlainText().strip()
        if not raw_tx:
            QMessageBox.warning(self, "Input Error", "Please enter a raw transaction hex.")
            return
        
        QMessageBox.information(self, "Decode", "Transaction decoding will be implemented when connected to the blockchain.")
    
    def sign_transaction(self):
        """Sign a transaction."""
        QMessageBox.information(self, "Sign", "Transaction signing will be implemented when connected to the blockchain.")
    
    def broadcast_transaction(self):
        """Broadcast a signed transaction."""
        QMessageBox.information(self, "Broadcast", "Transaction broadcasting will be implemented when connected to the blockchain.")
    
    def refresh_utxos(self):
        """Refresh UTXO list."""
        QMessageBox.information(self, "Refresh", "UTXO refresh will be implemented when connected to the blockchain.")
    
    def open_coin_control(self):
        """Open coin control dialog."""
        QMessageBox.information(self, "Coin Control", "Coin control will be implemented when connected to the blockchain.")
    
    def update_balance(self, balance_btc, balance_usd=None):
        """Update the balance display."""
        if hasattr(self, 'balance_label'):
            self.balance_label.setText(f"Balance: {balance_btc:.8f} BTC")
        if balance_usd is not None and hasattr(self, 'balance_usd_label'):
            self.balance_usd_label.setText(f"≈ ${balance_usd:.2f} USD")
    
    def update_transaction_history_display(self):
        """Update the transaction history display."""
        self.load_transaction_history()
