from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFont


class BitcoinSummary(QWidget):
    """Simple Bitcoin summary widget for the home page."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create a frame for styling
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setLineWidth(1)
        frame_layout = QVBoxLayout()
        frame.setLayout(frame_layout)
        
        # Title
        title = QLabel("Bitcoin Node Status")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        frame_layout.addWidget(title)
        
        # Connection status
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Connection:"))
        self.connection_status = QLabel("⚫ Disconnected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        conn_layout.addWidget(self.connection_status)
        conn_layout.addStretch()
        frame_layout.addLayout(conn_layout)
        
        # Block height
        block_layout = QHBoxLayout()
        block_layout.addWidget(QLabel("Block Height:"))
        self.block_height = QLabel("0")
        block_layout.addWidget(self.block_height)
        block_layout.addStretch()
        frame_layout.addLayout(block_layout)
        
        # Network
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("Network:"))
        self.network_label = QLabel("Unknown")
        network_layout.addWidget(self.network_label)
        network_layout.addStretch()
        frame_layout.addLayout(network_layout)
        
        # Connections
        connections_layout = QHBoxLayout()
        connections_layout.addWidget(QLabel("Peers:"))
        self.connections_label = QLabel("0")
        connections_layout.addWidget(self.connections_label)
        connections_layout.addStretch()
        frame_layout.addLayout(connections_layout)
        
        layout.addWidget(frame)
        
    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        """Update connection status."""
        if connected:
            self.connection_status.setText("🟢 Connected")
            self.connection_status.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.connection_status.setText("⚫ Disconnected")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            # Reset other values
            self.block_height.setText("0")
            self.network_label.setText("Unknown")
            self.connections_label.setText("0")
    
    @pyqtSlot(dict)
    def update_blockchain_info(self, info):
        """Update blockchain information."""
        blocks = info.get('blocks', 0)
        self.block_height.setText(f"{blocks:,}")
        
        chain = info.get('chain', 'Unknown')
        self.network_label.setText(chain.title())
    
    @pyqtSlot(dict)
    def update_network_info(self, info):
        """Update network information."""
        connections = info.get('connections', 0)
        self.connections_label.setText(str(connections))
