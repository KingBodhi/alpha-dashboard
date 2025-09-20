import os
import sys
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QScrollArea, QSpacerItem, QSizePolicy
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from app.widgets.block_tracker import BlockTracker
from app.widgets.network_summary import NetworkSummary
from app.ui.components import GlassCard, MetricCard, StatusIndicator, HolographicHeader, MetricsGrid, NodeCard
from app.ui.theme import APNTheme

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

cesium_path = os.path.join(base_path, 'assets', 'cesium.html')

class HomePage(QWidget):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the modern dashboard UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(20)
        
        # Header
        node_name = self.config.identity.node_id if self.config else "Unknown Node"
        header = HolographicHeader(
            "Alpha Protocol Network", 
            f"Decentralized Cloud Node - {node_name}"
        )
        main_layout.addWidget(header)
        
        # Scrollable content area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(24)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # Metrics Grid
        self.metrics_grid = MetricsGrid()
        self._setup_metrics()
        content_layout.addWidget(self.metrics_grid)
        
        # Network status row
        network_row = QHBoxLayout()
        
        # Network Map Card
        map_card = self._create_network_map_card()
        network_row.addWidget(map_card, 2)
        
        # Node Status Card
        status_card = self._create_node_status_card()
        network_row.addWidget(status_card, 1)
        
        content_layout.addLayout(network_row)
        
        # Recent Activity Card
        activity_card = self._create_activity_card()
        content_layout.addWidget(activity_card)
        
        # Add stretch at bottom
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
    def _setup_metrics(self):
        """Setup the metrics grid"""
        # Add key metrics for APN node contribution
        self.network_contribution_metric = self.metrics_grid.add_metric("Network Contribution", "0", "APN tokens", "Start earning", 0, 0)
        self.bandwidth_shared_metric = self.metrics_grid.add_metric("Bandwidth Shared", "0", "GB", "Contribute to earn", 0, 1)
        self.compute_contributed_metric = self.metrics_grid.add_metric("Compute Shared", "0", "hours", "Idle resources", 0, 2)
        self.storage_contributed_metric = self.metrics_grid.add_metric("Storage Shared", "0", "GB", "Available space", 0, 3)
        
    def _create_network_map_card(self):
        """Create the network map card"""
        # Web view for Cesium map
        self.web = QWebEngineView()
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.web.load(QUrl.fromLocalFile(cesium_path))
        self.web.setMinimumHeight(400)
        
        # Apply glass styling to web view
        self.web.setStyleSheet(f"""
            QWebEngineView {{
                border-radius: 12px;
                border: 1px solid {APNTheme.COLORS['border_primary']};
                background: {APNTheme.COLORS['bg_card']};
            }}
        """)
        
        map_card = GlassCard("Live Network Map", self.web)
        return map_card
        
    def _create_node_status_card(self):
        """Create node status display card"""
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setSpacing(16)
        
        # Node status indicator
        if self.config:
            node_status = StatusIndicator("online", "NODE ONLINE")
        else:
            node_status = StatusIndicator("offline", "NODE OFFLINE")
        status_layout.addWidget(node_status)
        
        # Connection details
        details = [
            ("Radio Status", "LoRa Connected"),
            ("Mesh ID", self.config.identity.node_id[:16] + "..." if self.config else "N/A"),
            ("Public Key", self.config.identity.public_key[:20] + "..." if self.config else "N/A"),
            ("Peers", "8 connected")
        ]
        
        for label, value in details:
            row = QHBoxLayout()
            
            label_widget = QLabel(f"{label}:")
            label_widget.setStyleSheet(f"""
                QLabel {{ 
                    color: {APNTheme.COLORS['text_secondary']};
                    font-weight: 500;
                    min-width: 100px;
                }}
            """)
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet(f"""
                QLabel {{ 
                    color: {APNTheme.COLORS['text_primary']};
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                }}
            """)
            
            row.addWidget(label_widget)
            row.addWidget(value_widget)
            row.addStretch()
            status_layout.addLayout(row)
        
        status_layout.addStretch()
        
        status_card = GlassCard("Node Status", status_widget)
        return status_card
        
    def _create_activity_card(self):
        """Create recent activity card"""
        activity_widget = QWidget()
        activity_layout = QVBoxLayout(activity_widget)
        
        # Activity list
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                background: {APNTheme.COLORS['glass_secondary']};
                border: 1px solid {APNTheme.COLORS['border_primary']};
                border-radius: 6px;
                padding: 12px;
                margin: 2px 0px;
                color: {APNTheme.COLORS['text_primary']};
            }}
            QListWidget::item:hover {{
                background: {APNTheme.COLORS['glass_primary']};
                border: 1px solid {APNTheme.COLORS['alpha_gold']};
            }}
        """)
        
        # Add some sample activities
        activities = [
            "🟢 Node started successfully",
            "📡 Connected to 3 mesh peers",
            "💬 Received message from apn_f4a2b1c8",
            "🔄 Synchronized with Bitcoin network",
            "📊 Performance metrics updated"
        ]
        
        for activity in activities:
            self.activity_list.addItem(activity)
        
        activity_layout.addWidget(self.activity_list)
        
        activity_card = GlassCard("Recent Activity", activity_widget)
        return activity_card

    def update_nodes(self, nodes):
        """Update the dashboard with node data from Meshtastic"""
        # Calculate more accurate online/offline counts
        total = len(nodes)
        
        # Count actually active nodes (heard from recently)
        import time
        current_time = time.time()
        recently_active = 0
        local_nodes = 0
        
        for node_id, node_info in nodes.items():
            last_heard = node_info.get('lastHeard', 0)
            
            # Count as recently active if heard in last 30 minutes
            if last_heard > 0 and (current_time - last_heard) < 1800:
                recently_active += 1
            
            # Count local/direct nodes (usually have stronger signal or direct connection)
            snr = node_info.get('snr', 0)
            if snr > 5:  # Strong signal indicates local node
                local_nodes += 1
        
        offline = total - recently_active
        
        # Update the metrics in our modern dashboard
        if hasattr(self, 'network_contribution_metric'):
            self.network_contribution_metric.update_metric(
                recently_active, 
                "active nodes", 
                f"↑ {local_nodes} local" if local_nodes > 0 else "Network connected"
            )
        
        # Update other metrics with more realistic data
        if hasattr(self, 'bandwidth_shared_metric'):
            self.bandwidth_shared_metric.update_metric(
                local_nodes * 2.5, "MB", f"Via {local_nodes} local nodes"
            )
        
        # Update activity list with accurate info
        if hasattr(self, 'activity_list'):
            if recently_active > 0:
                self.activity_list.addItem(f"📡 Connected to mesh: {recently_active} active nodes ({local_nodes} local)")
            else:
                self.activity_list.addItem("📡 Mesh network connected (scanning for active nodes...)")
            
        # Update map with node positions (only show recently active nodes)
        if hasattr(self, 'web'):
            mapped_nodes = 0
            for node_id, info in nodes.items():
                last_heard = info.get('lastHeard', 0)
                
                # Only map recently active nodes with positions
                if last_heard > 0 and (current_time - last_heard) < 1800:
                    user = info.get("user", {})
                    name = user.get("longName", f"Node-{node_id[-4:]}")
                    short_id = node_id.replace("^", "") if "^" in node_id else node_id
                    pos = info.get("position")
                    
                    if pos:
                        lat = pos.get("latitude")
                        lon = pos.get("longitude")
                        if lat is not None and lon is not None:
                            js = f"addOrUpdateNode('{short_id}', {lat}, {lon}, '{name}');"
                            self.web.page().runJavaScript(js)
                            mapped_nodes += 1
            
            print(f"🗺️ Mapped {mapped_nodes} active nodes with GPS coordinates")
        
        # Log the realistic update
        print(f"📊 Dashboard: {total} total nodes, {recently_active} active, {local_nodes} local, {offline} inactive")
