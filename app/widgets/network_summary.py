from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel

class NetworkSummary(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.total_label = QLabel("Total Nodes: 0")
        self.online_label = QLabel("Online: 0")
        self.offline_label = QLabel("Offline: 0")

        layout.addWidget(self.total_label)
        layout.addWidget(self.online_label)
        layout.addWidget(self.offline_label)

    def update(self, total, online, offline):
        self.total_label.setText(f"Total Nodes: {total}")
        self.online_label.setText(f"Online: {online}")
        self.offline_label.setText(f"Offline: {offline}")
