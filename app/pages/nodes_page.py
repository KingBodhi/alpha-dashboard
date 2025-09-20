from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel
from app.widgets.network_summary import NetworkSummary
from app.widgets.block_tracker import BlockTracker

class NodesPage(QWidget):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Live Network Summary"))
        self.summary = NetworkSummary()
        layout.addWidget(self.summary)

        layout.addWidget(QLabel("Block Tracker"))
        self.blocks = BlockTracker()
        layout.addWidget(self.blocks)

        layout.addWidget(QLabel("Connected Nodes"))
        self.list = QListWidget()
        layout.addWidget(self.list)

    def update_nodes(self, nodes):
        total = len(nodes)
        online = sum(1 for n in nodes.values() if n.get("online", True))
        offline = total - online
        self.summary.update(total, online, offline)

        self.list.clear()
        for node_id, info in nodes.items():
            user = info.get("user", {})
            name = user.get("longName", "(no name)")
            short_id = node_id.replace("^", "")
            is_online = info.get("online", True)
            status = "Online" if is_online else "Offline"
            self.list.addItem(f"{name} [{short_id}] - {status}")
