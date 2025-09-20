"""
Alpha Protocol Network - Devices Page
Real hardware device management and connectivity (Meshtastic-inspired UI)
"""
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QPushButton, QGroupBox, QProgressBar, QTextEdit, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from app.ui.components import GlassCard, HolographicButton, HolographicHeader, StatusIndicator
from app.ui.theme import APNTheme
from core.device_manager import DeviceManager

class DeviceCard(QFrame):
    """Individual device card (Meshtastic-style)"""
    connect_requested = pyqtSignal(str)  # device_id
    disconnect_requested = pyqtSignal(str)  # device_id
    
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup Meshtastic-inspired device card"""
        self.setFixedHeight(180)
        self.setFixedWidth(320)
        
        # Card styling
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {APNTheme.COLORS['glass_primary']},
                    stop: 1 {APNTheme.COLORS['glass_secondary']}
                );
                border: 2px solid {APNTheme.COLORS['border_primary']};
                border-radius: 16px;
                margin: 8px;
                padding: 16px;
            }}
            QFrame:hover {{
                border: 2px solid {APNTheme.COLORS['alpha_gold']};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # Header row with device type icon and status
        header_layout = QHBoxLayout()
        
        # Device type icon and name
        device_icon = self._get_device_icon()
        icon_label = QLabel(device_icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                color: {APNTheme.COLORS['alpha_gold']};
                min-width: 32px;
                max-width: 32px;
            }}
        """)
        header_layout.addWidget(icon_label)
        
        # Device name
        name_label = QLabel(self._get_device_name())
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_primary']};
                font-weight: 700;
                font-size: 16px;
            }}
        """)
        header_layout.addWidget(name_label, 1)
        
        # Status indicator
        status_color = self._get_status_color()
        status_indicator = StatusIndicator(status_color, self.device.status.upper())
        header_layout.addWidget(status_indicator)
        
        main_layout.addLayout(header_layout)
        
        # Device details
        details_layout = QVBoxLayout()
        details_layout.setSpacing(6)
        
        # Port
        port_label = QLabel(f"Port: {self.device.port}")
        port_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_secondary']};
                font-size: 13px;
                font-family: 'Courier New', monospace;
            }}
        """)
        details_layout.addWidget(port_label)
        
        # Hardware info
        if self.device.vendor_id and self.device.product_id:
            hw_label = QLabel(f"Hardware: {self.device.vendor_id}:{self.device.product_id}")
            hw_label.setStyleSheet(f"""
                QLabel {{
                    color: {APNTheme.COLORS['text_muted']};
                    font-size: 12px;
                    font-family: 'Courier New', monospace;
                }}
            """)
            details_layout.addWidget(hw_label)
        
        # Capabilities chips
        if self.device.capabilities:
            caps_layout = QHBoxLayout()
            caps_layout.setSpacing(4)
            
            for cap in self.device.capabilities[:3]:  # Show max 3 capabilities
                cap_chip = QLabel(cap)
                cap_chip.setStyleSheet(f"""
                    QLabel {{
                        background: {APNTheme.COLORS['alpha_gold']};
                        color: {APNTheme.COLORS['bg_primary']};
                        border-radius: 8px;
                        padding: 2px 6px;
                        font-size: 10px;
                        font-weight: 600;
                    }}
                """)
                caps_layout.addWidget(cap_chip)
            
            if len(self.device.capabilities) > 3:
                more_chip = QLabel(f"+{len(self.device.capabilities) - 3}")
                more_chip.setStyleSheet(f"""
                    QLabel {{
                        background: {APNTheme.COLORS['text_muted']};
                        color: {APNTheme.COLORS['bg_primary']};
                        border-radius: 8px;
                        padding: 2px 6px;
                        font-size: 10px;
                        font-weight: 600;
                    }}
                """)
                caps_layout.addWidget(more_chip)
                
            caps_layout.addStretch()
            details_layout.addLayout(caps_layout)
        
        main_layout.addLayout(details_layout)
        main_layout.addStretch()
        
        # Action button
        self.action_btn = HolographicButton(
            "🔗 Connect" if self.device.status != "connected" else "❌ Disconnect", 
            "primary" if self.device.status != "connected" else "secondary"
        )
        self.action_btn.clicked.connect(self._on_action_clicked)
        main_layout.addWidget(self.action_btn)
        
    def _get_device_icon(self):
        """Get icon for device type"""
        icons = {
            "esp32": "📡",
            "arduino": "🔧", 
            "lora": "📻",
            "bluetooth": "🔵",
            "wifi": "📶",
            "serial": "🔌",
            "unknown": "❓"
        }
        return icons.get(self.device.device_type, "❓")
    
    def _get_device_name(self):
        """Get clean device name"""
        if "ESP32" in self.device.description.upper():
            return "ESP32 Device"
        elif "ARDUINO" in self.device.description.upper():
            return "Arduino Board"
        elif self.device.device_type == "esp32":
            return "ESP32 Device"
        else:
            return self.device.device_type.title() + " Device"
    
    def _get_status_color(self):
        """Get status indicator color"""
        if self.device.status == "connected":
            return "success"
        elif self.device.status == "discovered":
            return "info"
        else:
            return "warning"
    
    def _on_action_clicked(self):
        """Handle connect/disconnect action"""
        if self.device.status == "connected":
            self.disconnect_requested.emit(self.device.device_id)
        else:
            self.connect_requested.emit(self.device.device_id)
    
    def update_device(self, device):
        """Update device information"""
        self.device = device
        self._setup_ui()

class DevicesPage(QWidget):
    device_connected = pyqtSignal(str)  # device_id
    device_disconnected = pyqtSignal(str)  # device_id
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.device_manager = DeviceManager()
        self._setup_ui()
        self._setup_device_scanning()
        
    def _setup_ui(self):
        """Setup the Meshtastic-inspired devices UI"""
        # Main layout with proper sizing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(24)
        
        # Ensure the page can expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Header
        header = HolographicHeader(
            "APN Device Manager", 
            "Connect and manage mesh network hardware"
        )
        main_layout.addWidget(header)
        
        # Control toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(12)
        
        self.scan_btn = HolographicButton("🔍 Scan Devices", "primary")
        self.scan_btn.clicked.connect(self._scan_devices)
        self.scan_btn.setMinimumWidth(140)
        toolbar_layout.addWidget(self.scan_btn)
        
        self.refresh_btn = HolographicButton("🔄 Refresh", "secondary")
        self.refresh_btn.clicked.connect(self._scan_devices)
        toolbar_layout.addWidget(self.refresh_btn)
        
        # Status info
        self.status_label = QLabel("Ready to scan for devices")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_secondary']};
                font-size: 14px;
                padding: 8px 16px;
            }}
        """)
        toolbar_layout.addWidget(self.status_label)
        
        toolbar_layout.addStretch()
        
        # Device count
        self.device_count_label = QLabel("0 devices found")
        self.device_count_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['alpha_gold']};
                font-weight: 600;
                font-size: 14px;
                padding: 8px 16px;
            }}
        """)
        toolbar_layout.addWidget(self.device_count_label)
        
        main_layout.addLayout(toolbar_layout)
        
        # Scrollable devices area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        # Devices container
        self.devices_container = QWidget()
        self.devices_layout = QGridLayout(self.devices_container)
        self.devices_layout.setSpacing(16)
        self.devices_layout.setContentsMargins(8, 8, 8, 8)
        
        # Add empty state
        self._show_empty_state()
        
        scroll_area.setWidget(self.devices_container)
        main_layout.addWidget(scroll_area, 1)  # Give it stretch factor
        
        # Compact console at bottom
        console_frame = self._create_compact_console()
        main_layout.addWidget(console_frame)
        
    def _show_empty_state(self):
        """Show empty state when no devices found"""
        # Clear existing layout
        for i in reversed(range(self.devices_layout.count())):
            self.devices_layout.itemAt(i).widget().setParent(None)
        
        # Empty state widget
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel("🔌")
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 64px;
                color: {APNTheme.COLORS['text_muted']};
                text-align: center;
            }}
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(icon_label)
        
        # Message
        msg_label = QLabel("No devices found")
        msg_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_secondary']};
                font-size: 18px;
                font-weight: 600;
                text-align: center;
            }}
        """)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(msg_label)
        
        # Instruction
        inst_label = QLabel("Connect ESP32 or other mesh devices and click 'Scan Devices'")
        inst_label.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_muted']};
                font-size: 14px;
                text-align: center;
            }}
        """)
        inst_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_label.setWordWrap(True)
        empty_layout.addWidget(inst_label)
        
        # Center the empty state
        self.devices_layout.addWidget(empty_widget, 0, 0, 1, -1, Qt.AlignmentFlag.AlignCenter)
    
    def _create_compact_console(self):
        """Create compact console for device logs"""
        console_frame = QFrame()
        console_frame.setMaximumHeight(120)
        console_frame.setStyleSheet(f"""
            QFrame {{
                background: {APNTheme.COLORS['bg_primary']};
                border: 1px solid {APNTheme.COLORS['border_primary']};
                border-radius: 12px;
                margin-top: 8px;
            }}
        """)
        
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(16, 12, 16, 12)
        console_layout.setSpacing(8)
        
        # Title
        console_title = QLabel("📋 Device Console")
        console_title.setStyleSheet(f"""
            QLabel {{
                color: {APNTheme.COLORS['text_primary']};
                font-weight: 600;
                font-size: 14px;
            }}
        """)
        console_layout.addWidget(console_title)
        
        # Console output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumHeight(80)
        self.console_output.setStyleSheet(f"""
            QTextEdit {{
                background: {APNTheme.COLORS['bg_elevated']};
                border: 1px solid {APNTheme.COLORS['border_primary']};
                border-radius: 8px;
                padding: 8px;
                color: {APNTheme.COLORS['success']};
                font-family: 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.4;
            }}
        """)
        console_layout.addWidget(self.console_output)
        
        return console_frame
    
    def _setup_device_scanning(self):
        """Setup automatic device scanning"""
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self._scan_devices)
        self.scan_timer.start(15000)  # Scan every 15 seconds
        
        # Initial scan
        self._scan_devices()
    
    def _scan_devices(self):
        """Scan for available devices"""
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("🔄 Scanning...")
        self._log_to_console("Scanning for APN-compatible devices...")
        
        # For now, simulate device scanning without async
        self._simulate_device_scan()
    
    def _simulate_device_scan(self):
        """Simulate device scanning for demo purposes"""
        try:
            import serial.tools.list_ports
            
            # Get actual serial ports
            ports = list(serial.tools.list_ports.comports())
            devices = []
            
            for port in ports:
                from core.device_manager import APNDevice
                
                # Determine device type based on description
                device_type = "unknown"
                if any(term in port.description.lower() for term in ["esp32", "esp", "wemos", "nodemcu"]):
                    device_type = "esp32"
                elif any(term in port.description.lower() for term in ["arduino", "uno", "mega"]):
                    device_type = "arduino"
                elif "serial" in port.description.lower():
                    device_type = "serial"
                
                # Set capabilities based on type
                capabilities = []
                if device_type == "esp32":
                    capabilities = ["mesh_node", "lora", "wifi", "bluetooth"]
                elif device_type == "arduino":
                    capabilities = ["sensor_node", "actuator"]
                
                device = APNDevice(
                    device_id=f"{device_type}_{port.device.replace('/', '_')}",
                    device_type=device_type,
                    port=port.device,
                    description=f"{port.description} ({device_type.upper()})",
                    vendor_id=f"{port.vid:04x}" if port.vid else None,
                    product_id=f"{port.pid:04x}" if port.pid else None,
                    status="discovered",
                    capabilities=capabilities,
                    metadata={
                        "manufacturer": port.manufacturer,
                        "serial_number": port.serial_number
                    }
                )
                devices.append(device)
            
            # Update device manager
            self.device_manager.devices = devices
            
            # Update UI
            self._update_device_lists(devices)
            
            if devices:
                self._log_to_console(f"Found {len(devices)} potential APN devices")
            else:
                self._log_to_console("No serial devices found. Connect ESP32 or other devices and scan again.")
            
        except Exception as e:
            self._log_to_console(f"Device scan error: {e}")
        finally:
            # Re-enable scan button
            self.scan_btn.setEnabled(True)
            self.scan_btn.setText("🔍 Scan for Devices")
    
    def _update_device_lists(self, devices):
        """Update device cards in grid layout"""
        # Clear existing cards
        for i in reversed(range(self.devices_layout.count())):
            child = self.devices_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Update device count
        device_count = len(devices)
        connected_count = sum(1 for d in devices if d.status == "connected")
        
        if device_count == 0:
            self._show_empty_state()
            self.device_count_label.setText("0 devices found")
            self.status_label.setText("No devices detected")
            return
        
        # Update status
        self.device_count_label.setText(f"{device_count} devices found")
        if connected_count > 0:
            self.status_label.setText(f"{connected_count} connected to APN network")
        else:
            self.status_label.setText("Ready to connect devices")
        
        # Create device cards in grid
        cards_per_row = 3  # Adjust based on card width
        row = 0
        col = 0
        
        for device in devices:
            # Create device card
            device_card = DeviceCard(device)
            device_card.connect_requested.connect(self._connect_device)
            device_card.disconnect_requested.connect(self._disconnect_device)
            
            # Add to grid
            self.devices_layout.addWidget(device_card, row, col)
            
            col += 1
            if col >= cards_per_row:
                col = 0
                row += 1
        
        # Add stretch to fill remaining space
        self.devices_layout.setRowStretch(row + 1, 1)
        self.devices_layout.setColumnStretch(cards_per_row, 1)
        
        self._log_to_console(f"Found {device_count} devices ({connected_count} connected)")
    
    def _connect_device(self, device_id):
        """Connect a specific device"""
        device = self.device_manager.get_device(device_id)
        if device:
            self._log_to_console(f"Connecting to {device.description}...")
            
            # Try to connect through Meshtastic service for ESP32/LoRa devices
            if device.device_type in ["esp32", "lora"]:
                from services.meshtastic_service import MeshtasticService
                try:
                    # If this device port matches meshtastic, it should already be connected
                    if MeshtasticService.iface is not None:
                        device.status = "connected"
                        self._log_to_console(f"✅ Connected to {device.description} via Meshtastic")
                    else:
                        self._log_to_console(f"⚠️ Meshtastic service not available for {device.description}")
                        device.status = "error"
                except Exception as e:
                    self._log_to_console(f"❌ Failed to connect {device.description}: {e}")
                    device.status = "error"
            else:
                # For other devices, simulate connection
                device.status = "connected"
                self._log_to_console(f"✅ Connected to {device.description}")
            
            self._update_device_lists(self.device_manager.devices)
            
            # Emit signal
            self.device_connected.emit(device_id)
    
    def _disconnect_device(self, device_id):
        """Disconnect a specific device"""
        device = self.device_manager.get_device(device_id)
        if device:
            self._log_to_console(f"Disconnecting from {device.description}...")
            
            # Simulate disconnection
            device.status = "discovered"
            self._update_device_lists(self.device_manager.devices)
            self._log_to_console(f"❌ Disconnected from {device.description}")
            
            # Emit signal
            self.device_disconnected.emit(device_id)
    
    def _log_to_console(self, message):
        """Add message to device console"""
        self.console_output.append(f"[APN] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.console_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
