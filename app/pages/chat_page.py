from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QLabel

class ChatPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Chat"))
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        layout.addWidget(self.chat_log)

        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message...")
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.input)
        input_layout.addWidget(send_button)
        layout.addLayout(input_layout)

    def append_message(self, msg):
        self.chat_log.append(msg)

    def send_message(self):
        text = self.input.text().strip()
        if text:
            from services.meshtastic_service import MeshtasticService
            MeshtasticService.iface.sendText(text)
            self.append_message(f"You: {text}")
            self.input.clear()
