from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout,
    QListWidget, QListWidgetItem, QSplitter, QTabWidget, QScrollArea,
    QMessageBox, QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
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
        self.init_ui()
        
    def init_ui(self):
        """Initialize the transaction page UI."""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title = QLabel("Bitcoin Transactions")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        # Create tabs for different transaction functions
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Send transaction tab
        self.send_tab = self.create_send_tab()
        tabs.addTab(self.send_tab, "Send Bitcoin")
        
        # Receive tab
        self.receive_tab = self.create_receive_tab()
        tabs.addTab(self.receive_tab, "Receive Bitcoin")
        
        # Transaction history tab
        self.history_tab = self.create_history_tab()
        tabs.addTab(self.history_tab, "Transaction History")
        
        # Transaction builder tab (advanced)
        self.builder_tab = self.create_builder_tab()
        tabs.addTab(self.builder_tab, "Advanced Builder")
        
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
        self.custom_fee_input.setDecimals(8)
        self.custom_fee_input.setSuffix(" BTC")
        self.custom_fee_input.setVisible(False)
        fee_layout.addWidget(self.custom_fee_input)
        
        self.fee_combo.currentTextChanged.connect(self.on_fee_selection_changed)
        
        send_form.addRow("Fee:", fee_layout)
        
        # Description (optional)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Optional description for your records")
        send_form.addRow("Description:", self.description_input)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QFormLayout()
        advanced_group.setLayout(advanced_layout)
        
        self.rbf_checkbox = QCheckBox("Replace-by-Fee (RBF)")
        self.rbf_checkbox.setChecked(True)
        advanced_layout.addRow("Options:", self.rbf_checkbox)
        
        form_layout.addWidget(send_group)
        form_layout.addWidget(advanced_group)
        
        # Transaction preview
        preview_group = QGroupBox("Transaction Preview")
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
        
        if not recipient or amount <= 0:
            QMessageBox.warning(self, "Input Error", "Please enter a valid recipient address and amount.")
            return
        
        # Create preview text
        preview = f"""Transaction Preview:
        
To: {recipient}
Amount: {amount:.8f} BTC
Fee: {self.get_selected_fee():.8f} BTC
Total: {amount + self.get_selected_fee():.8f} BTC

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
        """Send the transaction (placeholder for now)."""
        # Create transaction object
        transaction = {
            "recipient": self.recipient_input.text().strip(),
            "amount": self.amount_input.value(),
            "fee": self.get_selected_fee(),
            "description": self.description_input.text().strip(),
            "rbf": self.rbf_checkbox.isChecked(),
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "txid": f"pending_{len(self.transaction_history) + 1}"
        }
        
        # Add to history
        self.transaction_history.append(transaction)
        
        # Emit signal for future integration
        self.transaction_created.emit(transaction)
        
        # Show confirmation
        QMessageBox.information(
            self, 
            "Transaction Created", 
            f"Transaction created successfully!\n\nNote: This is a demo transaction. No actual Bitcoin was sent.\n\nTransaction ID: {transaction['txid']}"
        )
        
        # Clear form
        self.clear_send_form()
        
        # Refresh history
        self.load_transaction_history()
    
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
        # This would integrate with the profile page to get the actual address
        # For now, show a placeholder
        QMessageBox.information(self, "QR Code", "Payment QR code generation will be implemented when connected to the blockchain.")
    
    def load_transaction_history(self):
        """Load transaction history into the list."""
        self.transaction_list.clear()
        
        for tx in self.transaction_history:
            status_icon = "⏳" if tx["status"] == "pending" else "✅" if tx["status"] == "confirmed" else "❌"
            type_icon = "📤" if "recipient" in tx else "📥"
            
            item_text = f"{status_icon} {type_icon} {tx.get('amount', 0):.8f} BTC - {tx.get('description', 'No description')}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, tx)
            self.transaction_list.addItem(item)
    
    def refresh_transaction_history(self):
        """Refresh transaction history from the blockchain."""
        # Placeholder - would integrate with Bitcoin service
        QMessageBox.information(self, "Refresh", "Transaction history refresh will be implemented when connected to the blockchain.")
    
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
        # This would be connected to input field changes
        pass
    
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
    
    def set_wallet_address(self, address):
        """Set the wallet address for receiving transactions."""
        self.receive_address_label.setText(address)
    
    def update_balance(self, balance_btc, balance_usd=None):
        """Update the balance display."""
        self.balance_label.setText(f"Balance: {balance_btc:.8f} BTC")
        if balance_usd is not None:
            self.balance_usd_label.setText(f"≈ ${balance_usd:.2f} USD")
