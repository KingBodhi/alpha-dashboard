import os
import json
from pathlib import Path
from app.pages import globals
from app.widgets.bitcoin_wallet_widget import BitcoinWalletWidget
from app.utils.bitcoin_wallet_descriptor_generator import BitcoinWalletDescriptorGenerator
# ====================================================
# Bitcoin Core descriptor-based address generation
# ====================================================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QListWidget, QHBoxLayout, QListWidgetItem, QInputDialog, QDialog,
    QFormLayout, QTextEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

import qrcode

PROFILE_DIR = Path.home() / ".alpha_protocol_network"
PROFILE_PATH = PROFILE_DIR / "profile.json"


class ProfilePage(QWidget):
    def copy_apn_url_to_clipboard(self):
        url = globals.PUBLIC_WEB_URL
        if url != "":
            QGuiApplication.clipboard().setText(url)
            QMessageBox.information(self, "Copied!", f"URL copied to clipboard:\n{url}")
        else:
            QMessageBox.warning(self, "Not Ready", "APN URL is not yet available.")

    def __init__(self, bitcoin_service=None):
        super().__init__()

        self.devices = []
        self.bitcoin_service = bitcoin_service
        self.descriptor_generator = None
        self.wallet_addresses = {}
        self.wallet_loaded = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setStyleSheet("QLabel { font-size: 14px; }")

        # User Identity Section
        title = QLabel("User Profile (Alpha Protocol Node Identity)")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)

        # Bitcoin Core Connection Status (prominent display)
        self.connection_status_label = QLabel("🔴 Bitcoin Core: Not Connected")
        self.connection_status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #d32f2f; padding: 10px; border: 2px solid #d32f2f; border-radius: 5px;")
        self.layout.addWidget(self.connection_status_label)

        # Connection instructions
        self.connection_instructions = QLabel(
            "⚠️ Bitcoin Core connection required to load wallet addresses.\n"
            "Please ensure Bitcoin Core is running with RPC enabled."
        )
        self.connection_instructions.setStyleSheet("color: #ff9800; font-style: italic; padding: 5px;")
        self.connection_instructions.setWordWrap(True)
        self.layout.addWidget(self.connection_instructions)

        # Refresh wallet state button
        self.refresh_wallet_button = QPushButton("🔄 Check Bitcoin Core Connection")
        self.refresh_wallet_button.setStyleSheet(
            "QPushButton { "
            "background-color: #2196F3; color: white; font-weight: bold; "
            "padding: 8px 16px; border: none; border-radius: 4px; "
            "} "
            "QPushButton:hover { background-color: #1976D2; } "
            "QPushButton:pressed { background-color: #0D47A1; }"
        )
        self.refresh_wallet_button.clicked.connect(self.refresh_wallet_state)
        self.layout.addWidget(self.refresh_wallet_button)

        # Wallet address section (initially hidden)
        self.wallet_section = QWidget()
        self.wallet_layout = QVBoxLayout()
        self.wallet_section.setLayout(self.wallet_layout)
        
        self.address_label = QLabel("Bitcoin Address: (waiting for Bitcoin Core connection...)")
        self.address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.wallet_layout.addWidget(self.address_label)

        # Wallet status
        self.wallet_status_label = QLabel("Wallet Status: Waiting for Bitcoin Core...")
        self.wallet_status_label.setStyleSheet("color: #666; font-style: italic;")
        self.wallet_layout.addWidget(self.wallet_status_label)

        # Address type selector
        address_type_layout = QHBoxLayout()
        address_type_layout.addWidget(QLabel("Address Type:"))
        self.address_type_combo = QComboBox()
        self.address_type_combo.addItems(["Segwit (bech32)", "Legacy (P2PKH)", "P2SH-wrapped Segwit"])
        self.address_type_combo.currentTextChanged.connect(self.on_address_type_changed)
        self.address_type_combo.setEnabled(False)  # Disabled until Bitcoin Core connects
        address_type_layout.addWidget(self.address_type_combo)
        address_type_layout.addStretch()
        self.wallet_layout.addLayout(address_type_layout)

        # Bitcoin wallet widget for blockchain sync
        self.bitcoin_wallet = BitcoinWalletWidget()
        self.wallet_layout.addWidget(self.bitcoin_wallet)
        
        # Initially hide wallet section
        self.wallet_section.hide()
        self.layout.addWidget(self.wallet_section)
        
        # DO NOT initialize descriptor generator until Bitcoin Core connects
        # This ensures only Bitcoin Core wallets can be loaded

        self.qr_label = QLabel()
        self.layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.layout.addWidget(QLabel("Nickname:"))
        self.nickname_input = QLineEdit()
        self.layout.addWidget(self.nickname_input)

        self.copy_url_button = QPushButton("Copy APN URL")
        self.copy_url_button.clicked.connect(self.copy_apn_url_to_clipboard)
        self.layout.addWidget(self.copy_url_button)
        self.layout.addWidget(QLabel("Role:"))
        self.role_select = QComboBox()
        self.role_select.addItems(["Standard", "Master", "Relay", "Gateway"])
        self.layout.addWidget(self.role_select)

        self.save_button = QPushButton("Save Profile")
        self.save_button.clicked.connect(self.save_profile)
        self.layout.addWidget(self.save_button)

        self.layout.addWidget(QLabel(" "))

        # Devices Section
        devices_title = QLabel("Your Devices")
        devices_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(devices_title)

        self.device_list = QListWidget()
        self.layout.addWidget(self.device_list)

        device_buttons = QHBoxLayout()
        self.add_device_button = QPushButton("Add Device")
        self.add_device_button.clicked.connect(self.add_device)
        device_buttons.addWidget(self.add_device_button)

        self.edit_device_button = QPushButton("Edit Selected")
        self.edit_device_button.clicked.connect(self.edit_selected_device)
        device_buttons.addWidget(self.edit_device_button)

        self.delete_device_button = QPushButton("Delete Selected")
        self.delete_device_button.clicked.connect(self.delete_selected_device)
        device_buttons.addWidget(self.delete_device_button)

        self.layout.addLayout(device_buttons)

        self.layout.addStretch()

        # Load Profile
        self.load_or_create_profile()

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)

    def setup_descriptor_generator(self):
        """Setup the descriptor generator with Bitcoin service."""
        try:
            self.descriptor_generator = BitcoinWalletDescriptorGenerator(self.bitcoin_service)
            print("✅ Descriptor generator initialized")
        except Exception as e:
            print(f"⚠️ Could not initialize descriptor generator: {e}")
            self.descriptor_generator = None

    def load_or_create_profile(self):
        if not PROFILE_DIR.exists():
            PROFILE_DIR.mkdir(parents=True)

        if PROFILE_PATH.exists():
            with open(PROFILE_PATH, "r") as f:
                data = json.load(f)
        else:
            # Initialize with placeholder data - will be populated from wallet
            data = {
                "wallet_based": True,  # Flag to indicate this uses wallet addresses
                "address": None,  # Will be populated from wallet after Bitcoin Core connects
                "nickname": "AlphaNode",
                "role": "Standard",
                "devices": []
            }
            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)

        # Load basic profile data (non-wallet related)
        self.nickname_input.setText(data.get("nickname", ""))
        self.role_select.setCurrentText(data.get("role", "Standard"))
        self.devices = data.get("devices", [])
        self.refresh_device_list()

    def on_bitcoin_core_connected(self):
        """Called when Bitcoin Core connection is established."""
        try:
            print("🟢 Bitcoin Core connected - initializing wallet integration")
            
            # Update connection status
            self.connection_status_label.setText("🟢 Bitcoin Core: Connected")
            self.connection_status_label.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: #2e7d32; padding: 10px; "
                "border: 2px solid #2e7d32; border-radius: 5px;"
            )
            
            # Hide connection instructions and refresh button
            self.connection_instructions.hide()
            self.refresh_wallet_button.hide()
            
            # Show wallet section
            self.wallet_section.show()
            
            # Enable address type selector
            self.address_type_combo.setEnabled(True)
            
            # Now setup descriptor generator and load wallet addresses
            self.setup_descriptor_generator()
            if self.descriptor_generator:
                self.load_wallet_addresses()
                self.wallet_loaded = True
            else:
                raise Exception("Failed to initialize descriptor generator")
                
        except Exception as e:
            print(f"❌ Error setting up wallet after Bitcoin Core connection: {e}")
            self.wallet_status_label.setText(f"Wallet Status: ❌ Error: {str(e)}")
            self.address_label.setText("Bitcoin Address: (wallet setup failed)")

    def on_bitcoin_core_disconnected(self):
        """Called when Bitcoin Core connection is lost."""
        print("🔴 Bitcoin Core disconnected - disabling wallet functionality")
        
        # Update connection status
        self.connection_status_label.setText("🔴 Bitcoin Core: Not Connected")
        self.connection_status_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #d32f2f; padding: 10px; "
            "border: 2px solid #d32f2f; border-radius: 5px;"
        )
        
        # Show connection instructions and refresh button
        self.connection_instructions.show()
        self.refresh_wallet_button.show()
        
        # Hide wallet section
        self.wallet_section.hide()
        
        # Disable address type selector
        self.address_type_combo.setEnabled(False)
        
        # Clear wallet data
        self.descriptor_generator = None
        self.wallet_addresses = {}
        self.wallet_loaded = False
        
        # Reset status
        self.wallet_status_label.setText("Wallet Status: ⏳ Waiting for Bitcoin Core connection...")
        self.address_label.setText("Bitcoin Address: (Bitcoin Core connection required)")
        
        print("📋 Profile loaded - waiting for Bitcoin Core connection to load wallet addresses")

    def refresh_wallet_state(self):
        """Refresh wallet state - check for Bitcoin Core connection and reload wallet."""
        try:
            print("🔄 Refreshing wallet state...")
            
            # Update button state
            self.refresh_wallet_button.setText("🔄 Checking...")
            self.refresh_wallet_button.setEnabled(False)
            
            # Check if we have a bitcoin service
            if not self.bitcoin_service:
                print("⚠️ No Bitcoin service available")
                self.show_refresh_error("No Bitcoin service configured. Please restart the application.")
                return
            
            # Try to connect/reconnect to Bitcoin Core
            try:
                connection_success = self.bitcoin_service.connect_to_node()
                if connection_success:
                    print("✅ Bitcoin Core connection successful")
                    # Trigger wallet initialization
                    self.on_bitcoin_core_connected()
                    self.show_refresh_success("Successfully connected to Bitcoin Core and loaded wallet!")
                else:
                    print("❌ Bitcoin Core connection failed")
                    self.on_bitcoin_core_disconnected()
                    self.show_refresh_error(
                        "Could not connect to Bitcoin Core.\n"
                        "Please ensure:\n"
                        "• Bitcoin Core is running\n"
                        "• RPC is enabled\n"
                        "• Correct RPC credentials in config"
                    )
            except Exception as e:
                print(f"❌ Connection error: {e}")
                self.on_bitcoin_core_disconnected()
                self.show_refresh_error(f"Connection error: {str(e)}")
                
        except Exception as e:
            print(f"❌ Refresh wallet state error: {e}")
            self.show_refresh_error(f"Refresh failed: {str(e)}")
        finally:
            # Reset button state
            self.refresh_wallet_button.setText("🔄 Check Bitcoin Core Connection")
            self.refresh_wallet_button.setEnabled(True)

    def show_refresh_success(self, message):
        """Show success message for wallet refresh."""
        QMessageBox.information(
            self, 
            "Wallet Refresh Successful", 
            message
        )

    def show_refresh_error(self, message):
        """Show error message for wallet refresh."""
        QMessageBox.warning(
            self, 
            "Wallet Refresh Failed", 
            message
        )
    def load_wallet_addresses(self):
        """Load addresses from Bitcoin Core wallet."""
        try:
            self.wallet_status_label.setText("Wallet Status: 🔄 Loading addresses...")
            
            # Get all address types from wallet
            self.wallet_addresses = self.descriptor_generator.get_all_address_types()
            
            # Set primary address (prefer bech32)
            self.address = self.wallet_addresses.get('bech32')
            if not self.address:
                self.address = self.wallet_addresses.get('p2sh_segwit')
            if not self.address:
                self.address = self.wallet_addresses.get('legacy')
                
            if self.address:
                self.address_label.setText(f"Bitcoin Address:\n{self.address}")
                self.bitcoin_wallet.set_address(self.address)
                
                # Set address type combo
                addr_type = self.descriptor_generator._detect_address_type(self.address)
                if addr_type == 'bech32':
                    self.address_type_combo.setCurrentText("Segwit (bech32)")
                elif addr_type == 'p2sh-segwit':
                    self.address_type_combo.setCurrentText("P2SH-wrapped Segwit")
                else:
                    self.address_type_combo.setCurrentText("Legacy (P2PKH)")
                
                self.generate_qr_code(self.address)
                self.wallet_status_label.setText("Wallet Status: ✅ Connected to Bitcoin Core wallet")
                
                print(f"✅ Loaded wallet address: {self.address}")
                
                # Save the wallet address to profile
                self.save_wallet_address_to_profile()
                
            else:
                raise Exception("No addresses available in wallet")
                
        except Exception as e:
            print(f"❌ Error loading wallet addresses: {e}")
            self.wallet_status_label.setText(f"Wallet Status: ❌ Error: {str(e)}")
            self.address_label.setText("Bitcoin Address: (error loading from wallet)")

    def save_wallet_address_to_profile(self):
        """Save current wallet address to profile."""
        try:
            if PROFILE_PATH.exists():
                with open(PROFILE_PATH, "r") as f:
                    data = json.load(f)
            else:
                data = {}
                
            data.update({
                "wallet_based": True,
                "address": self.address,
                "wallet_addresses": self.wallet_addresses,
                "nickname": self.nickname_input.text(),
                "role": self.role_select.currentText(),
                "devices": self.devices
            })
            
            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)
                
        except Exception as e:
            print(f"⚠️ Could not save wallet address to profile: {e}")

    # Legacy profile loader removed - Bitcoin Core wallet required

    def save_profile(self):
        """Save profile - Bitcoin Core wallet addresses only."""
        nickname = self.nickname_input.text().strip()
        role = self.role_select.currentText()

        if len(nickname) < 1:
            self.show_message("Error", "Nickname cannot be empty.")
            return

        # Use wallet-based profile saving if wallet is loaded
        if self.wallet_loaded and hasattr(self, 'address'):
            self.save_wallet_address_to_profile()
        else:
            # Save basic profile data only
            data = {
                "wallet_based": True,
                "address": None,  # Will be populated when Bitcoin Core connects
                "nickname": nickname,
                "role": role,
                "devices": self.devices
            }

            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)

        self.show_message("Profile Saved", "Your profile has been updated successfully!")

    def generate_qr_code(self, text):
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_path = PROFILE_DIR / "address_qr.png"
        img.save(img_path)

        pixmap = QPixmap(str(img_path))
        self.qr_label.setPixmap(pixmap)

    def refresh_device_list(self):
        self.device_list.clear()
        for device in self.devices:
            item_text = f"{device.get('nickname', '(Unnamed)')} | {device.get('role', 'Unknown')}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, device)
            self.device_list.addItem(item)

    def add_device(self):
        device = self.prompt_device_dialog()
        if device:
            self.devices.append(device)
            self.refresh_device_list()
            self.save_profile()

    def edit_selected_device(self):
        item = self.device_list.currentItem()
        if not item:
            self.show_message("Error", "No device selected.")
            return

        device = item.data(Qt.ItemDataRole.UserRole)
        updated_device = self.prompt_device_dialog(device)
        if updated_device:
            idx = self.devices.index(device)
            self.devices[idx] = updated_device
            self.refresh_device_list()
            self.save_profile()

    def delete_selected_device(self):
        item = self.device_list.currentItem()
        if not item:
            self.show_message("Error", "No device selected.")
            return

        device = item.data(Qt.ItemDataRole.UserRole)
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete device '{device.get('nickname', '(Unnamed)')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.devices.remove(device)
            self.refresh_device_list()
            self.save_profile()

    def prompt_device_dialog(self, device=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Device Info")
        layout = QFormLayout(dialog)

        id_input = QLineEdit(device.get("device_id", "") if device else "")
        nickname_input = QLineEdit(device.get("nickname", "") if device else "")
        role_input = QComboBox()
        role_input.addItems(["Relay", "Gateway", "Standard"])
        if device:
            role_input.setCurrentText(device.get("role", "Relay"))
        notes_input = QTextEdit(device.get("notes", "") if device else "")

        layout.addRow("Device ID:", id_input)
        layout.addRow("Nickname:", nickname_input)
        layout.addRow("Role:", role_input)
        layout.addRow("Notes:", notes_input)

        buttons = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)

        def accept():
            dialog.accept()

        def reject():
            dialog.reject()

        save_button.clicked.connect(accept)
        cancel_button.clicked.connect(reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return {
                "device_id": id_input.text().strip(),
                "nickname": nickname_input.text().strip(),
                "role": role_input.currentText(),
                "notes": notes_input.toPlainText().strip()
            }
        return None

    def get_bitcoin_wallet(self):
        """Get reference to the Bitcoin wallet widget for service integration."""
        return self.bitcoin_wallet
    
    def get_bitcoin_address(self):
        """Get the current Bitcoin address."""
        return self.address

    def on_address_type_changed(self, address_type):
        """Handle address type change."""
        try:
            if self.descriptor_generator and self.wallet_addresses:
                # Use wallet-based addresses
                if address_type.startswith("Segwit"):
                    new_address = self.wallet_addresses.get('bech32')
                elif address_type.startswith("P2SH"):
                    new_address = self.wallet_addresses.get('p2sh_segwit')
                else:  # Legacy
                    new_address = self.wallet_addresses.get('legacy')
                
                if new_address and new_address != self.address:
                    self.address = new_address
                    self.address_label.setText(f"Bitcoin Address:\n{self.address}")
                    self.bitcoin_wallet.set_address(self.address)
                    self.generate_qr_code(self.address)
                    
                    print(f"🔄 Wallet address type changed to {address_type}: {self.address}")
                    
                    # Save the updated profile
                    self.save_wallet_address_to_profile()
                    
            else:
                QMessageBox.warning(
                    self, "Bitcoin Core Required",
                    "Address type changes require a Bitcoin Core wallet connection.\n"
                    "Please ensure Bitcoin Core is running and connected."
                )
                
        except Exception as e:
            print(f"❌ Error changing address type: {e}")
            QMessageBox.warning(self, "Error", f"Could not change address type: {e}")

    def set_bitcoin_service(self, bitcoin_service):
        """Set the Bitcoin service after initialization."""
        self.bitcoin_service = bitcoin_service
        self.setup_descriptor_generator()
        
        # Reload profile with wallet integration if connected
        if bitcoin_service and bitcoin_service.is_connected:
            try:
                self.load_wallet_addresses()
            except Exception as e:
                print(f"⚠️ Could not load wallet addresses after setting service: {e}")
