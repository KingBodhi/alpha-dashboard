from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDockWidget, QListWidget, QStackedWidget
from app.pages.home_page import HomePage
from app.pages.apn_page import APNPage
from app.pages.chat_page import ChatPage
from app.pages.map_page import MapPage
from app.pages.nodes_page import NodesPage
from app.pages.profile_page import ProfilePage
from services.meshtastic_service import MeshtasticService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alpha Protocol Network (APN)")
        self.resize(1200, 700)

        # Drawer
        self.drawer = QDockWidget("Menu", self)
        self.drawer.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.drawer_list = QListWidget()
        self.drawer_list.addItems(["Home", "APN", "Chat", "Map", "Nodes", "Profile"])
        self.drawer_list.currentRowChanged.connect(self.navigate)
        self.drawer.setWidget(self.drawer_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.drawer)

        # Pages
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home_page = HomePage()
        self.apn_page = APNPage()
        self.chat_page = ChatPage()
        self.map_page = MapPage()
        self.nodes_page = NodesPage()
        self.profile_page = ProfilePage()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.apn_page)
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.map_page)
        self.stack.addWidget(self.nodes_page)
        self.stack.addWidget(self.profile_page)


        # Meshtastic Service
        self.service = MeshtasticService()
        self.service.new_message.connect(self.chat_page.append_message)
        self.service.update_nodes.connect(self.update_nodes_all)

    def start_service(self):
        """Call this AFTER the window is shown to avoid QWidget initialization errors."""
        self.service.start()

    def navigate(self, index):
        self.stack.setCurrentIndex(index)

    def update_nodes_all(self, nodes):
        self.home_page.update_nodes(nodes)
        self.map_page.update_nodes(nodes)
        self.nodes_page.update_nodes(nodes)
