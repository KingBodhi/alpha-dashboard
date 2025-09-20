import os
import json
from pathlib import Path
from app.pages import globals

# Simplified profile without Bitcoin dependencies for now

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
    QComboBox, QListWidget, QHBoxLayout, QListWidgetItem, QInputDialog, QDialog,
    QFormLayout, QTextEdit
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

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

    def __init__(self, config=None):
        super().__init__()
        self.config = config

        self.devices = []

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setStyleSheet("QLabel { font-size: 14px; }")

        # User Identity Section
        title = QLabel("User Profile (Alpha Protocol Node Identity)")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title)

        if self.config:
            node_id = self.config.identity.node_id
            self.address_label = QLabel(f"Node ID: {node_id}")
        else:
            self.address_label = QLabel("Node ID: (not configured)")
        self.address_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.layout.addWidget(self.address_label)

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

    def load_or_create_profile(self):
        if not PROFILE_DIR.exists():
            PROFILE_DIR.mkdir(parents=True)

        if PROFILE_PATH.exists():
            with open(PROFILE_PATH, "r") as f:
                data = json.load(f)
        else:
            data = {
                "nickname": "AlphaNode",
                "role": "Standard", 
                "devices": []
            }
            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)

        self.nickname_input.setText(data.get("nickname", ""))
        self.role_select.setCurrentText(data.get("role", "Standard"))
        self.devices = data.get("devices", [])

        self.refresh_device_list()

    def save_profile(self):
        nickname = self.nickname_input.text().strip()
        role = self.role_select.currentText()

        if len(nickname) < 1:
            self.show_message("Error", "Nickname cannot be empty.")
            return

        data = {
            "nickname": nickname,
            "role": role,
            "devices": self.devices
        }

        with open(PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=4)

        self.show_message("Profile Saved", "Your profile has been updated successfully!")

    # QR code generation removed for now

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
