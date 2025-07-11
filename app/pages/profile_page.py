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

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setStyleSheet("QLabel { font-size: 14px; }")

        # User Identity Section
        title = QLabel("User Profile (Alpha Protocol Node Identity)")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)

        self.address_label = QLabel("Bitcoin Address: (loading from wallet...)")
        self.address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(self.address_label)

        # Wallet status
        self.wallet_status_label = QLabel("Wallet Status: Connecting...")
        self.wallet_status_label.setStyleSheet("color: #666; font-style: italic;")
        self.layout.addWidget(self.wallet_status_label)

        # Address type selector
        address_type_layout = QHBoxLayout()
        address_type_layout.addWidget(QLabel("Address Type:"))
        self.address_type_combo = QComboBox()
        self.address_type_combo.addItems(["Segwit (bech32)", "Legacy (P2PKH)", "P2SH-wrapped Segwit"])
        self.address_type_combo.currentTextChanged.connect(self.on_address_type_changed)
        address_type_layout.addWidget(self.address_type_combo)
        address_type_layout.addStretch()
        self.layout.addLayout(address_type_layout)

        # Bitcoin wallet widget for blockchain sync
        self.bitcoin_wallet = BitcoinWalletWidget()
        self.layout.addWidget(self.bitcoin_wallet)
        
        # Initialize descriptor generator if bitcoin service is available
        if self.bitcoin_service:
            self.setup_descriptor_generator()

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
                "address": None,  # Will be populated from wallet
                "nickname": "AlphaNode",
                "role": "Standard",
                "devices": []
            }
            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)

        # Load profile data
        self.nickname_input.setText(data.get("nickname", ""))
        self.role_select.setCurrentText(data.get("role", "Standard"))
        self.devices = data.get("devices", [])

        # Load wallet addresses if descriptor generator is available
        if self.descriptor_generator:
            try:
                self.load_wallet_addresses()
            except Exception as e:
                print(f"⚠️ Could not load wallet addresses: {e}")
                self.wallet_status_label.setText("Wallet Status: ⚠️ Connection failed")
                self.address_label.setText("Bitcoin Address: (wallet connection failed)")
        else:
            # Fallback to legacy behavior if no Bitcoin service
            self.load_legacy_profile(data)
            
        self.refresh_device_list()

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

    def load_legacy_profile(self, data):
        """Load legacy profile with standalone key generation."""
        try:
            # Import the old generator for backward compatibility
            from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
            
            if "private_key" in data:
                # Existing legacy profile
                self.private_key = data["private_key"]
                self.address = data["address"]
            else:
                # Generate new legacy profile
                generator = BitcoinAddressGenerator()
                self.private_key = generator.private_key_wif
                self.address = generator.get_native_segwit_address()
                
                # Save new data
                data.update({
                    "private_key": self.private_key,
                    "address": self.address,
                    "legacy_address": generator.get_legacy_address(),
                    "p2sh_segwit_address": generator.get_p2sh_segwit_address()
                })
                
                with open(PROFILE_PATH, "w") as f:
                    json.dump(data, f, indent=4)

            self.address_label.setText(f"Bitcoin Address:\n{self.address}")
            self.bitcoin_wallet.set_address(self.address)
            self.generate_qr_code(self.address)
            self.wallet_status_label.setText("Wallet Status: 📍 Using standalone address (no Bitcoin Core)")
            
            # Set address type combo
            if self.address.startswith('bc1') or self.address.startswith('tb1'):
                self.address_type_combo.setCurrentText("Segwit (bech32)")
            elif self.address.startswith('3') or self.address.startswith('2'):
                self.address_type_combo.setCurrentText("P2SH-wrapped Segwit")
            else:
                self.address_type_combo.setCurrentText("Legacy (P2PKH)")
                
        except Exception as e:
            print(f"❌ Error loading legacy profile: {e}")
            self.wallet_status_label.setText("Wallet Status: ❌ Error loading profile")

    def save_profile(self):
        nickname = self.nickname_input.text().strip()
        role = self.role_select.currentText()

        if len(nickname) < 1:
            self.show_message("Error", "Nickname cannot be empty.")
            return

        data = {
            "private_key": self.private_key,
            "address": self.address,
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
                    
            elif hasattr(self, 'private_key') and self.private_key:
                # Fallback to legacy generator
                from app.utils.bitcoin_address_generator import BitcoinAddressGenerator
                generator = BitcoinAddressGenerator(self.private_key)
                
                if address_type.startswith("Segwit"):
                    new_address = generator.get_native_segwit_address()
                elif address_type.startswith("P2SH"):
                    new_address = generator.get_p2sh_segwit_address()
                else:  # Legacy
                    new_address = generator.get_legacy_address()
                
                if new_address != self.address:
                    self.address = new_address
                    self.address_label.setText(f"Bitcoin Address:\n{self.address}")
                    self.bitcoin_wallet.set_address(self.address)
                    self.generate_qr_code(self.address)
                    
                    print(f"🔄 Legacy address type changed to {address_type}: {self.address}")
                    
                    # Save the updated profile
                    self.save_profile()
            else:
                QMessageBox.warning(self, "Error", "No wallet connection or private key available")
                
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
