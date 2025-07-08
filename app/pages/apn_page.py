import os
import json
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QGroupBox, QCheckBox, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt

# Paths
CONFIG_DIR = Path.home() / ".apn"
CONFIG_PATH = CONFIG_DIR / "node_config.json"
PROFILE_PATH = Path.home() / ".alpha_protocol_network" / "profile.json"

class APNPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alpha Protocol Network Control Panel")

        self.payment_address = self.load_payment_address()

        main_layout = QVBoxLayout(self)

        # ================
        # NODE IDENTITY
        # ================
        identity_group = QGroupBox("Node Identity")
        identity_layout = QGridLayout()

        identity_layout.addWidget(QLabel("Node ID:"), 0, 0)
        self.node_id_input = QLineEdit()
        self.node_id_input.setPlaceholderText("e.g. AlphaGenesis01")
        identity_layout.addWidget(self.node_id_input, 0, 1)

        identity_layout.addWidget(QLabel("Payment Address:"), 1, 0)
        self.payment_address_input = QLineEdit()
        self.payment_address_input.setText(self.payment_address)
        self.payment_address_input.setReadOnly(True)
        identity_layout.addWidget(self.payment_address_input, 1, 1)

        identity_group.setLayout(identity_layout)
        main_layout.addWidget(identity_group)

        # =====================
        # ACCESS POINT SETTINGS
        # =====================
        ap_group = QGroupBox("WiFi Access Point Settings")
        ap_layout = QGridLayout()

        ap_layout.addWidget(QLabel("SSID:"), 0, 0)
        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("AlphaProtocolNetwork")
        ap_layout.addWidget(self.ssid_input, 0, 1)

        ap_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Minimum 8 characters")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        ap_layout.addWidget(self.password_input, 1, 1)

        ap_layout.addWidget(QLabel("Channel:"), 2, 0)
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("6")
        ap_layout.addWidget(self.channel_input, 2, 1)

        self.bridging_checkbox = QCheckBox("Allow connected nodes to access WWW")
        ap_layout.addWidget(self.bridging_checkbox, 3, 0, 1, 2)

        self.vpn_checkbox = QCheckBox("Enable VPN Encryption for APN traffic")
        ap_layout.addWidget(self.vpn_checkbox, 4, 0, 1, 2)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("Start Access Point")
        self.start_button.clicked.connect(self.start_access_point)
        self.stop_button = QPushButton("Stop Access Point")
        self.stop_button.clicked.connect(self.stop_access_point)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        ap_layout.addLayout(button_row, 5, 0, 1, 2)

        ap_group.setLayout(ap_layout)
        main_layout.addWidget(ap_group)

        # ==================
        # ROLES AND SERVICES
        # ==================
        # Relay Node
        relay_group = QGroupBox("Relay Node")
        relay_layout = QVBoxLayout()
        self.relay_checkbox = QCheckBox("Enable this node as a Relay")
        relay_layout.addWidget(self.relay_checkbox)
        relay_group.setLayout(relay_layout)
        main_layout.addWidget(relay_group)

        # Storage Node
        storage_group = QGroupBox("Storage Node")
        storage_layout = QGridLayout()
        self.storage_checkbox = QCheckBox("Enable Storage Service")
        storage_layout.addWidget(self.storage_checkbox, 0, 0, 1, 2)
        self.storage_gb_label = QLabel("Available Storage (GB):")
        self.storage_gb_input = QLineEdit()
        self.storage_price_label = QLabel("Price per GB (Alpha):")
        self.storage_price_input = QLineEdit()
        storage_layout.addWidget(self.storage_gb_label, 1, 0)
        storage_layout.addWidget(self.storage_gb_input, 1, 1)
        storage_layout.addWidget(self.storage_price_label, 2, 0)
        storage_layout.addWidget(self.storage_price_input, 2, 1)
        storage_group.setLayout(storage_layout)
        main_layout.addWidget(storage_group)

        # Compute Node
        compute_group = QGroupBox("Compute Node")
        compute_layout = QGridLayout()
        self.compute_checkbox = QCheckBox("Enable Compute Service")
        compute_layout.addWidget(self.compute_checkbox, 0, 0, 1, 2)
        self.compute_cores_label = QLabel("CPU Cores:")
        self.compute_cores_input = QLineEdit()
        self.compute_price_label = QLabel("Price per Second (Alpha):")
        self.compute_price_input = QLineEdit()
        compute_layout.addWidget(self.compute_cores_label, 1, 0)
        compute_layout.addWidget(self.compute_cores_input, 1, 1)
        compute_layout.addWidget(self.compute_price_label, 2, 0)
        compute_layout.addWidget(self.compute_price_input, 2, 1)
        compute_group.setLayout(compute_layout)
        main_layout.addWidget(compute_group)

        # Bridge / Gateway
        bridge_group = QGroupBox("Internet Bridge / Gateway")
        bridge_layout = QGridLayout()
        self.bridge_checkbox = QCheckBox("Enable Internet Bridging")
        bridge_layout.addWidget(self.bridge_checkbox, 0, 0, 1, 2)
        self.bridge_region_label = QLabel("Region:")
        self.bridge_region_input = QLineEdit()
        self.bridge_price_label = QLabel("Price per MB (Alpha):")
        self.bridge_price_input = QLineEdit()
        bridge_layout.addWidget(self.bridge_region_label, 1, 0)
        bridge_layout.addWidget(self.bridge_region_input, 1, 1)
        bridge_layout.addWidget(self.bridge_price_label, 2, 0)
        bridge_layout.addWidget(self.bridge_price_input, 2, 1)
        bridge_group.setLayout(bridge_layout)
        main_layout.addWidget(bridge_group)

        # ==================
        # SAVE / LOAD BUTTONS
        # ==================
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Config")
        self.save_button.clicked.connect(self.save_config)
        self.load_button = QPushButton("Load Config")
        self.load_button.clicked.connect(self.load_config)
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.load_button)
        main_layout.addLayout(buttons_layout)

        main_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Auto-load
        self.load_config()

    # ================
    # PAYMENT ADDRESS
    # ================
    def load_payment_address(self):
        try:
            with open(PROFILE_PATH) as f:
                data = json.load(f)
                return data.get("address", "")
        except Exception:
            return ""

    # ================
    # SAVE CONFIG
    # ================
    def save_config(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            config = {
                "nodeId": self.node_id_input.text().strip(),
                "paymentAddress": self.payment_address_input.text().strip(),
                "roles": [],
                "settings": {}
            }

            if self.relay_checkbox.isChecked():
                config["roles"].append("Relay")

            if self.storage_checkbox.isChecked():
                config["roles"].append("Storage")
                config["settings"]["storage"] = {
                    "availableGB": int(self.storage_gb_input.text()),
                    "pricePerGB": int(self.storage_price_input.text())
                }

            if self.compute_checkbox.isChecked():
                config["roles"].append("Compute")
                config["settings"]["compute"] = {
                    "cpuCores": int(self.compute_cores_input.text()),
                    "pricePerSecond": int(self.compute_price_input.text())
                }

            if self.bridge_checkbox.isChecked():
                config["roles"].append("Bridge")
                config["settings"]["bridge"] = {
                    "region": self.bridge_region_input.text().strip(),
                    "pricePerMB": int(self.bridge_price_input.text())
                }

            with open(CONFIG_PATH, "w") as f:
                json.dump(config, f, indent=2)

            QMessageBox.information(self, "Success", "Node config saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config: {e}")

    # ================
    # LOAD CONFIG
    # ================
    def load_config(self):
        if not CONFIG_PATH.exists():
            return

        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)

            self.node_id_input.setText(config.get("nodeId", ""))
            self.payment_address_input.setText(config.get("paymentAddress", ""))
            roles = config.get("roles", [])

            self.relay_checkbox.setChecked("Relay" in roles)
            self.storage_checkbox.setChecked("Storage" in roles)
            self.compute_checkbox.setChecked("Compute" in roles)
            self.bridge_checkbox.setChecked("Bridge" in roles)

            settings = config.get("settings", {})
            if "storage" in settings:
                self.storage_gb_input.setText(str(settings["storage"].get("availableGB", "")))
                self.storage_price_input.setText(str(settings["storage"].get("pricePerGB", "")))
            if "compute" in settings:
                self.compute_cores_input.setText(str(settings["compute"].get("cpuCores", "")))
                self.compute_price_input.setText(str(settings["compute"].get("pricePerSecond", "")))
            if "bridge" in settings:
                self.bridge_region_input.setText(settings["bridge"].get("region", ""))
                self.bridge_price_input.setText(str(settings["bridge"].get("pricePerMB", "")))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config: {e}")

    # ================
    # ACCESS POINT MANAGEMENT (LOCAL ONLY)
    # ================
    def start_access_point(self):
        ssid = self.ssid_input.text().strip()
        password = self.password_input.text().strip()
        channel = self.channel_input.text().strip() or "6"

        if len(ssid) < 1:
            self.show_message("Error", "SSID cannot be empty.")
            return
        if len(password) < 8:
            self.show_message("Error", "Password must be at least 8 characters.")
            return

        try:
            hostapd_conf = f"""
interface=wlan0
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""
            os.makedirs("/etc/hostapd", exist_ok=True)
            with open("/etc/hostapd/hostapd.conf", "w") as f:
                f.write(hostapd_conf)

            subprocess.run(["sudo", "systemctl", "restart", "hostapd"], check=True)
            subprocess.run(["sudo", "systemctl", "restart", "dnsmasq"], check=True)

            if self.bridging_checkbox.isChecked():
                subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
                subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"], check=True)

            self.show_message("Success", f"Access Point '{ssid}' started successfully!")
        except Exception as e:
            self.show_message("Error", f"Failed to start AP: {e}")

    def stop_access_point(self):
        try:
            subprocess.run(["sudo", "systemctl", "stop", "hostapd"], check=True)
            subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], check=True)
            subprocess.run(["sudo", "iptables", "-t", "nat", "-D", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"], check=True)
            self.show_message("Stopped", "Access Point stopped successfully.")
        except Exception as e:
            self.show_message("Error", f"Failed to stop AP: {e}")

    def show_message(self, title, message):
        QMessageBox.information(self, title, message)
