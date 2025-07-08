from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QLabel, QSpinBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from app.config.bitcoin_config import BITCOIN_RPC_CONFIG


class BitcoinConfigDialog(QDialog):
    """Dialog for configuring Bitcoin RPC connection settings."""
    
    settings_changed = pyqtSignal(dict)  # Emitted when settings are saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bitcoin RPC Configuration")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        self.load_current_settings()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Connection settings group
        conn_group = QGroupBox("RPC Connection Settings")
        conn_layout = QFormLayout()
        conn_group.setLayout(conn_layout)
        
        # Host
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("127.0.0.1")
        conn_layout.addRow("Host:", self.host_edit)
        
        # Port
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(8332)
        conn_layout.addRow("Port:", self.port_spinbox)
        
        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("rpcuser")
        conn_layout.addRow("Username:", self.username_edit)
        
        # Password
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("rpcpassword")
        conn_layout.addRow("Password:", self.password_edit)
        
        layout.addWidget(conn_group)
        
        # Update settings group
        update_group = QGroupBox("Update Settings")
        update_layout = QFormLayout()
        update_group.setLayout(update_layout)
        
        # Update interval
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1000, 60000)  # 1 second to 1 minute
        self.interval_spinbox.setSuffix(" ms")
        self.interval_spinbox.setValue(5000)
        update_layout.addRow("Update Interval:", self.interval_spinbox)
        
        layout.addWidget(update_group)
        
        # Info label
        info_label = QLabel("⚠️ Changes require reconnection to take effect")
        info_label.setStyleSheet("color: orange; font-style: italic;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
    def load_current_settings(self):
        """Load current settings into the form."""
        self.host_edit.setText(BITCOIN_RPC_CONFIG["rpc_host"])
        self.port_spinbox.setValue(BITCOIN_RPC_CONFIG["rpc_port"])
        self.username_edit.setText(BITCOIN_RPC_CONFIG["rpc_user"])
        self.password_edit.setText(BITCOIN_RPC_CONFIG["rpc_password"])
        self.interval_spinbox.setValue(BITCOIN_RPC_CONFIG["update_interval"])
        
    def get_settings(self):
        """Get settings from the form."""
        return {
            "rpc_host": self.host_edit.text().strip() or "127.0.0.1",
            "rpc_port": self.port_spinbox.value(),
            "rpc_user": self.username_edit.text().strip() or "admin",
            "rpc_password": self.password_edit.text(),
            "update_interval": self.interval_spinbox.value(),
        }
        
    def test_connection(self):
        """Test the connection with current settings."""
        from services.bitcoin_service import BitcoinService
        from PyQt6.QtWidgets import QMessageBox
        
        settings = self.get_settings()
        
        # Create temporary service for testing
        test_service = BitcoinService(
            rpc_user=settings["rpc_user"],
            rpc_password=settings["rpc_password"],
            rpc_host=settings["rpc_host"],
            rpc_port=settings["rpc_port"]
        )
        
        self.test_button.setEnabled(False)
        self.test_button.setText("Testing...")
        
        # Test connection
        if test_service.connect_to_node():
            # Get some basic info to verify it's working
            try:
                info = test_service.send_raw_command('getblockchaininfo')
                chain = info.get('chain', 'Unknown') if info else 'Unknown'
                blocks = info.get('blocks', 0) if info else 0
                
                QMessageBox.information(
                    self, 
                    "Connection Test Successful",
                    f"✅ Connected successfully!\n\n"
                    f"Chain: {chain}\n"
                    f"Blocks: {blocks:,}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Connection Test Warning", 
                    f"⚠️ Connected but error getting info:\n{e}"
                )
            
            test_service.disconnect()
            
        else:
            QMessageBox.critical(
                self,
                "Connection Test Failed",
                "❌ Could not connect to Bitcoin node.\n\n"
                "Please check your settings and ensure:\n"
                "• Bitcoin Core is running\n"
                "• RPC is enabled\n"
                "• Credentials are correct"
            )
        
        self.test_button.setEnabled(True)
        self.test_button.setText("Test Connection")
        
    def save_settings(self):
        """Save the settings and close dialog."""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        self.accept()
