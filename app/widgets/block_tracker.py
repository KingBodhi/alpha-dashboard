from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget

class BlockTracker(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list = QListWidget()
        layout.addWidget(self.list)

        self.load_blocks()

    def load_blocks(self):
        blocks = [
            {"height": 839998, "status": "confirmed"},
            {"height": 839999, "status": "confirmed"},
            {"height": 840000, "status": "confirmed"},
            {"height": 840001, "status": "upcoming"},
            {"height": 840002, "status": "upcoming"},
            {"height": 840003, "status": "upcoming"},
        ]
        self.list.clear()
        for block in blocks:
            icon = "✅" if block["status"] == "confirmed" else "🕒"
            self.list.addItem(f"{icon} Block {block['height']}")
