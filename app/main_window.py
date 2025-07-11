from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QMainWindow, QDockWidget, QListWidget, QStackedWidget
from app.pages.home_page import HomePage
from app.pages.apn_page import APNPage
from app.pages.chat_page import ChatPage
from app.pages.map_page import MapPage
from app.pages.nodes_page import NodesPage
from app.pages.profile_page import ProfilePage
from app.pages.bitcoin_page import BitcoinPage
from app.pages.transaction_page import TransactionPage
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
        self.drawer_list.addItems(["Home", "APN", "Chat", "Map", "Nodes", "Profile", "Bitcoin", "Transactions"])
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
        # Profile page will get Bitcoin service after it's created
        self.profile_page = ProfilePage()
        self.bitcoin_page = BitcoinPage()
        self.transaction_page = TransactionPage()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.apn_page)
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.map_page)
        self.stack.addWidget(self.nodes_page)
        self.stack.addWidget(self.profile_page)
        self.stack.addWidget(self.bitcoin_page)
        self.stack.addWidget(self.transaction_page)


        # Meshtastic Service
        self.service = MeshtasticService()
        self.service.new_message.connect(self.chat_page.append_message)
        self.service.update_nodes.connect(self.update_nodes_all)

        # Bitcoin Service
        self.bitcoin_service = BitcoinService()
        self.setup_bitcoin_connections()

    def start_service(self):
        """Call this AFTER the window is shown to avoid QWidget initialization errors."""
        # Start Meshtastic service first (fast)
        self.service.start()
        
        # Delay Bitcoin service initialization to avoid blocking UI
        QTimer.singleShot(1000, self._delayed_bitcoin_setup)
        
    def _delayed_bitcoin_setup(self):
        """Initialize Bitcoin service connections after UI is fully loaded."""
        # Note: Bitcoin monitoring is not auto-started - user must click Connect button
        print("🔧 Bitcoin service ready for connections")

    def setup_bitcoin_connections(self):
        """Setup connections between Bitcoin service and UI."""
        dashboard = self.bitcoin_page.get_dashboard()
        
        # Use queued connections to prevent blocking UI thread
        from PyQt6.QtCore import Qt
        
        # Connect Bitcoin service signals to dashboard slots
        self.bitcoin_service.connection_status_changed.connect(
            dashboard.update_connection_status, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.blockchain_info_updated.connect(
            dashboard.update_blockchain_info, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.network_info_updated.connect(
            dashboard.update_network_info, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.mempool_updated.connect(
            dashboard.update_mempool_info, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.new_block_received.connect(
            dashboard.add_new_block, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.peer_info_updated.connect(
            dashboard.update_peers_info, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.status_message.connect(
            dashboard.update_status_message, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.error_occurred.connect(
            dashboard.show_error_message, Qt.ConnectionType.QueuedConnection)
        
        # Connect Bitcoin service to profile page wallet widget
        profile_wallet = self.profile_page.get_bitcoin_wallet()
        self.bitcoin_service.connection_status_changed.connect(
            profile_wallet.update_connection_status, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.blockchain_info_updated.connect(
            profile_wallet.update_balance_from_blockchain, Qt.ConnectionType.QueuedConnection)
        
        # Connect address-specific signals
        self.bitcoin_service.address_balance_updated.connect(
            profile_wallet.update_address_balance, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.address_transactions_updated.connect(
            profile_wallet.update_address_transactions, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.address_performance_status.connect(
            profile_wallet.update_performance_status, Qt.ConnectionType.QueuedConnection)
        
        # Connect Bitcoin service to transaction page
        self.transaction_page.set_bitcoin_service(self.bitcoin_service)
        
        # Defer address operations to prevent blocking during startup
        QTimer.singleShot(100, self._setup_bitcoin_addresses)
        
        # Set up wallet service reference for manual updates
        profile_wallet.bitcoin_service = self.bitcoin_service
        
        # Set up Bitcoin service for profile page wallet functionality
        self.profile_page.set_bitcoin_service(self.bitcoin_service)
        
        # Connect Bitcoin service connection status to profile page
        self.bitcoin_service.connection_status_changed.connect(
            self._update_profile_connection_status, Qt.ConnectionType.QueuedConnection)
        
        # Connect Bitcoin service to home page summary
        self.bitcoin_service.connection_status_changed.connect(
            self.home_page.bitcoin_summary.update_connection_status, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.blockchain_info_updated.connect(
            self.home_page.bitcoin_summary.update_blockchain_info, Qt.ConnectionType.QueuedConnection)
        self.bitcoin_service.network_info_updated.connect(
            self.home_page.bitcoin_summary.update_network_info, Qt.ConnectionType.QueuedConnection)
        
        # Connect dashboard button to service
        dashboard.connect_button.clicked.connect(self.toggle_bitcoin_connection)
        dashboard.on_settings_changed = self.update_bitcoin_settings
        
        # Connect error signals
        self.bitcoin_service.error_occurred.connect(self.show_bitcoin_error)
    
    def _setup_bitcoin_addresses(self):
        """Setup Bitcoin addresses after UI initialization to prevent blocking."""
        try:
            # Get the profile's Bitcoin address (may involve crypto operations)
            bitcoin_address = self.profile_page.get_bitcoin_address()
            if bitcoin_address:
                self.bitcoin_service.add_address_to_monitor(bitcoin_address)
                self.transaction_page.set_wallet_address(bitcoin_address)
                print(f"✅ Bitcoin address monitoring configured: {bitcoin_address[:8]}...")
        except Exception as e:
            print(f"⚠️ Failed to setup Bitcoin address: {e}")
    
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

    def _update_profile_connection_status(self, connected):
        """Update profile page connection status when Bitcoin service connection changes."""
        try:
            if connected:
                # Bitcoin Core connected - trigger wallet initialization
                self.profile_page.on_bitcoin_core_connected()
            else:
                # Bitcoin Core disconnected - disable wallet functionality
                self.profile_page.on_bitcoin_core_disconnected()
        except Exception as e:
            print(f"⚠️ Error updating profile connection status: {e}")

    def navigate(self, index):
        self.stack.setCurrentIndex(index)

    def update_nodes_all(self, nodes):
        self.home_page.update_nodes(nodes)
        self.map_page.update_nodes(nodes)
        self.nodes_page.update_nodes(nodes)
