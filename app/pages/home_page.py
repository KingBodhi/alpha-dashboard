import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QScrollArea
from app.widgets.block_tracker import BlockTracker
from app.widgets.network_summary import NetworkSummary
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

cesium_path = os.path.join(base_path, 'assets', 'cesium.html')

class HomePage(QWidget):
    def __init__(self):
        super().__init__()

        # Scrollable container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)

        # BlockTracker
        layout.addWidget(QLabel("Block Tracker"))
        self.blocks = BlockTracker()
        layout.addWidget(self.blocks)

        # Network Summary
        layout.addWidget(QLabel("Live Network Summary"))
        self.summary = NetworkSummary()
        layout.addWidget(self.summary)

        # Map
        layout.addWidget(QLabel("Network Map"))
        self.web = QWebEngineView()
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web.load(QUrl.fromLocalFile(cesium_path))
        layout.addWidget(self.web)

        # Node List
        layout.addWidget(QLabel("Connected Nodes"))
        self.list = QListWidget()
        layout.addWidget(self.list)

        scroll_area.setWidget(container)

        page_layout = QVBoxLayout()
        page_layout.addWidget(scroll_area)
        self.setLayout(page_layout)

    def update_nodes(self, nodes):
        # Update network summary
        total = len(nodes)
        online = sum(1 for n in nodes.values() if n.get("online", True))
        offline = total - online
        self.summary.update(total, online, offline)

        # Update node list
        self.list.clear()
        for node_id, info in nodes.items():
            user = info.get("user", {})
            name = user.get("longName", "(no name)")
            short_id = node_id.replace("^", "")
            is_online = info.get("online", True)
            status = "Online" if is_online else "Offline"
            self.list.addItem(f"{name} [{short_id}] - {status}")

            # Update map markers
            pos = info.get("position")
            if pos:
                lat = pos.get("latitude")
                lon = pos.get("longitude")
                if lat is not None and lon is not None:
                    js = f"addOrUpdateNode('{short_id}', {lat}, {lon}, '{name}');"
                    self.web.page().runJavaScript(js)
