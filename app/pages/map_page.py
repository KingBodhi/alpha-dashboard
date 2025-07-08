import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QUrl

class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Network Map"))

        self.web = QWebEngineView()
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        map_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../assets/cesium.html'))
        self.web.load(QUrl.fromLocalFile(map_path))
        layout.addWidget(self.web)

    def update_nodes(self, nodes):
        for node_id, info in nodes.items():
            user = info.get("user", {})
            name = user.get("longName", "(no name)")
            pos = info.get("position")
            if pos:
                lat = pos.get("latitude")
                lon = pos.get("longitude")
                if lat is not None and lon is not None:
                    short_id = node_id.replace("^", "")
                    js = f"addOrUpdateNode('{short_id}', {lat}, {lon}, '{name}');"
                    self.web.page().runJavaScript(js)
