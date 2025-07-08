from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDockWidget, QListWidget, QStackedWidget
from app.pages.home_page import HomePage
from app.pages.apn_page import APNPage
from app.pages.chat_page import ChatPage
from app.pages.map_page import MapPage
from app.pages.nodes_page import NodesPage
from app.pages.profile_page import ProfilePage
from app.pages.bitcoin_page import BitcoinPage
from services.meshtastic_service import MeshtasticService
from services.bitcoin_service import BitcoinService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alpha Protocol Network (APN)")
        self.resize(1200, 700)

        # Drawer
        self.drawer = QDockWidget("Menu", self)
        self.drawer.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.drawer_list = QListWidget()
        self.drawer_list.addItems(["Home", "APN", "Chat", "Map", "Nodes", "Profile", "Bitcoin"])
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
        self.bitcoin_page = BitcoinPage()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.apn_page)
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.map_page)
        self.stack.addWidget(self.nodes_page)
        self.stack.addWidget(self.profile_page)
        self.stack.addWidget(self.bitcoin_page)


        # Meshtastic Service
        self.service = MeshtasticService()
        self.service.new_message.connect(self.chat_page.append_message)
        self.service.update_nodes.connect(self.update_nodes_all)

        # Bitcoin Service
        self.bitcoin_service = BitcoinService()
        self.setup_bitcoin_connections()

    def start_service(self):
        """Call this AFTER the window is shown to avoid QWidget initialization errors."""
        self.service.start()
        # Auto-start Bitcoin monitoring
        self.bitcoin_service.start_monitoring()

    def setup_bitcoin_connections(self):
        """Setup connections between Bitcoin service and UI."""
        dashboard = self.bitcoin_page.get_dashboard()
        
        # Connect Bitcoin service signals to dashboard slots
        self.bitcoin_service.connection_status_changed.connect(dashboard.update_connection_status)
        self.bitcoin_service.blockchain_info_updated.connect(dashboard.update_blockchain_info)
        self.bitcoin_service.network_info_updated.connect(dashboard.update_network_info)
        self.bitcoin_service.mempool_updated.connect(dashboard.update_mempool_info)
        self.bitcoin_service.new_block_received.connect(dashboard.add_new_block)
        self.bitcoin_service.peer_info_updated.connect(dashboard.update_peers_info)
        
        # Connect Bitcoin service to home page summary
        self.bitcoin_service.connection_status_changed.connect(self.home_page.bitcoin_summary.update_connection_status)
        self.bitcoin_service.blockchain_info_updated.connect(self.home_page.bitcoin_summary.update_blockchain_info)
        self.bitcoin_service.network_info_updated.connect(self.home_page.bitcoin_summary.update_network_info)
        
        # Connect dashboard button to service
        dashboard.connect_button.clicked.connect(self.toggle_bitcoin_connection)
        dashboard.on_settings_changed = self.update_bitcoin_settings
        
        # Connect error signals
        self.bitcoin_service.error_occurred.connect(self.show_bitcoin_error)
    
    def toggle_bitcoin_connection(self):
        """Toggle Bitcoin node connection."""
        if self.bitcoin_service.is_connected:
            self.bitcoin_service.disconnect()
        else:
            self.bitcoin_service.start_monitoring()
    
    def show_bitcoin_error(self, error_message):
        """Show Bitcoin error message."""
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Bitcoin Connection Error")
        msg.setText(error_message)
        msg.exec()
    
    def update_bitcoin_settings(self, settings):
        """Update Bitcoin service with new settings."""
        # Disconnect current service
        if self.bitcoin_service.is_connected:
            self.bitcoin_service.disconnect()
        
        # Update service settings
        self.bitcoin_service.rpc_user = settings["rpc_user"]
        self.bitcoin_service.rpc_password = settings["rpc_password"]
        self.bitcoin_service.rpc_host = settings["rpc_host"]
        self.bitcoin_service.rpc_port = settings["rpc_port"]
        self.bitcoin_service.update_timer.setInterval(settings["update_interval"])
        
        # Update global config (for future instances)
        from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
        BITCOIN_RPC_CONFIG.update(settings)
        
        print(f"✅ Bitcoin settings updated. Host: {settings['rpc_host']}:{settings['rpc_port']}")
        
        # Show message to user
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Settings Updated")
        msg.setText("Bitcoin RPC settings have been updated.\nClick 'Connect' to use the new settings.")
        msg.exec()

    def navigate(self, index):
        self.stack.setCurrentIndex(index)

    def update_nodes_all(self, nodes):
        self.home_page.update_nodes(nodes)
        self.map_page.update_nodes(nodes)
        self.nodes_page.update_nodes(nodes)
