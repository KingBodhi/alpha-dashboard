from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from app.ui.components import GlassCard, HolographicButton, HolographicHeader
from app.ui.theme import APNTheme

class ChatPage(QWidget):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup modern chat UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(20)
        
        # Header
        header = HolographicHeader("Mesh Chat", "Secure P2P Communication")
        main_layout.addWidget(header)
        
        # Chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setSpacing(16)
        
        # Chat log with modern styling
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(f"""
            QTextEdit {{
                background: {APNTheme.COLORS['bg_elevated']};
                border: 1px solid {APNTheme.COLORS['border_primary']};
                border-radius: 12px;
                padding: 16px;
                color: {APNTheme.COLORS['text_primary']};
                font-family: 'SF Mono', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background: {APNTheme.COLORS['bg_card']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {APNTheme.COLORS['alpha_gold']};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        chat_layout.addWidget(self.chat_log, 1)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.setSpacing(12)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type your message to the mesh network...")
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: {APNTheme.COLORS['bg_elevated']};
                border: 2px solid {APNTheme.COLORS['border_primary']};
                border-radius: 12px;
                padding: 16px 20px;
                color: {APNTheme.COLORS['text_primary']};
                font-size: 14px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 2px solid {APNTheme.COLORS['alpha_gold']};
            }}
        """)
        self.input.returnPressed.connect(self.send_message)
        
        send_button = HolographicButton("Send Message", "primary")
        send_button.clicked.connect(self.send_message)
        send_button.setMinimumWidth(140)
        
        input_layout.addWidget(self.input, 1)
        input_layout.addWidget(send_button)
        
        chat_layout.addLayout(input_layout)
        
        # Wrap in glass card
        chat_card = GlassCard("", chat_widget)
        main_layout.addWidget(chat_card)
        
        # Add welcome message
        self.append_message("🟢 Connected to Alpha Protocol Mesh Network")
        self.append_message("🔒 End-to-end encrypted communication enabled")

    def append_message(self, msg):
        self.chat_log.append(msg)

    def send_message(self):
        text = self.input.text().strip()
        if text:
            from services.meshtastic_service import MeshtasticService
            success = MeshtasticService.sendText(text)
            if success:
                self.append_message(f"📤 You: {text}")
            else:
                self.append_message(f"❌ Failed to send: {text}")
            self.input.clear()
