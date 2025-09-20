"""
Alpha Protocol Network - Modern UI Components
Holographic and glass-morphism style components
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPalette, QFont
from .theme import APNTheme


class GlowEffect(QGraphicsDropShadowEffect):
    """Custom glow effect for holographic UI elements"""
    
    def __init__(self, color=QColor(255, 215, 0, 77), blur_radius=20):
        super().__init__()
        self.setColor(color)
        self.setBlurRadius(blur_radius)
        self.setOffset(0, 0)


class HolographicButton(QPushButton):
    """Modern holographic button with glow effects"""
    
    def __init__(self, text="", variant="default", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self._setup_style()
        self._setup_effects()
        
    def _setup_style(self):
        """Apply holographic styling"""
        if self.variant == "primary":
            self.setStyleSheet(APNTheme.get_holographic_button_style("primary"))
        elif self.variant == "secondary":
            self.setStyleSheet(APNTheme.get_holographic_button_style("secondary"))
        else:
            self.setStyleSheet(APNTheme.get_holographic_button_style("ghost"))
            
        # Set font
        font = QFont("SF Pro Display", 14, QFont.Weight.Bold)
        self.setFont(font)
        
    def _setup_effects(self):
        """Add glow and shadow effects"""
        if self.variant == "primary":
            glow = GlowEffect(QColor(255, 215, 0, 100), 25)
            self.setGraphicsEffect(glow)


class GlassCard(QFrame):
    """Glass-morphism style card component"""
    
    def __init__(self, title="", content_widget=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.content_widget = content_widget
        self._setup_ui()
        self._apply_style()
        
    def _setup_ui(self):
        """Setup the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        if self.title:
            title_label = QLabel(self.title)
            title_label.setProperty("class", "heading")
            title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(title_label)
            
        # Content
        if self.content_widget:
            layout.addWidget(self.content_widget)
            
    def _apply_style(self):
        """Apply glass-morphism styling"""
        self.setStyleSheet(APNTheme.get_card_style())
        
        # Add subtle shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class StatusIndicator(QLabel):
    """Status indicator with color-coded states"""
    
    def __init__(self, status="offline", text="", parent=None):
        super().__init__(text, parent)
        self.status = status
        self._update_appearance()
        
    def set_status(self, status, text=""):
        """Update the status indicator"""
        self.status = status
        if text:
            self.setText(text)
        self._update_appearance()
        
    def _update_appearance(self):
        """Update visual appearance based on status"""
        status_styles = {
            "online": f"""
                QLabel {{
                    background-color: {APNTheme.COLORS['success']};
                    color: {APNTheme.COLORS['bg_primary']};
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 12px;
                }}
            """,
            "offline": f"""
                QLabel {{
                    background-color: {APNTheme.COLORS['error']};
                    color: white;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 12px;
                }}
            """,
            "warning": f"""
                QLabel {{
                    background-color: {APNTheme.COLORS['warning']};
                    color: {APNTheme.COLORS['bg_primary']};
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 12px;
                }}
            """,
            "info": f"""
                QLabel {{
                    background-color: {APNTheme.COLORS['info']};
                    color: white;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: 600;
                    font-size: 12px;
                }}
            """
        }
        
        self.setStyleSheet(status_styles.get(self.status, status_styles["offline"]))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class MetricCard(GlassCard):
    """Card for displaying metrics with large numbers"""
    
    def __init__(self, title, value, unit="", trend=None, parent=None):
        self.metric_value = value
        self.unit = unit
        self.trend = trend
        
        content = self._create_metric_content()
        super().__init__(title, content, parent)
        
    def _create_metric_content(self):
        """Create the metric display content"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Main value
        value_label = QLabel(str(self.metric_value))
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 36px;
                font-weight: 700;
                color: {APNTheme.COLORS['alpha_gold']};
                margin: 0px;
            }}
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        
        # Unit
        if self.unit:
            unit_label = QLabel(self.unit)
            unit_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    font-weight: 500;
                    color: {APNTheme.COLORS['text_secondary']};
                    margin: 0px;
                }}
            """)
            unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(unit_label)
            
        # Trend indicator
        if self.trend:
            trend_label = QLabel(self.trend)
            trend_color = APNTheme.COLORS['success'] if self.trend.startswith('↑') else APNTheme.COLORS['error']
            trend_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 12px;
                    font-weight: 600;
                    color: {trend_color};
                    margin-top: 8px;
                }}
            """)
            trend_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(trend_label)
        
        return widget
    
    def update_metric(self, value, unit="", trend=None):
        """Update the metric values"""
        self.metric_value = value
        self.unit = unit
        self.trend = trend
        
        # Find and update the value label
        for child in self.content_widget.findChildren(QLabel):
            if child.text() == str(self.metric_value):
                child.setText(str(value))
                break


class NodeCard(GlassCard):
    """Card for displaying node information"""
    
    def __init__(self, node_id, node_name, status="offline", details=None, parent=None):
        self.node_id = node_id
        self.node_name = node_name
        self.node_status = status
        self.details = details or {}
        
        content = self._create_node_content()
        super().__init__(f"Node: {node_name}", content, parent)
        
    def _create_node_content(self):
        """Create node information content"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Status and ID row
        status_row = QHBoxLayout()
        
        # Status indicator
        status_indicator = StatusIndicator(self.node_status, self.node_status.upper())
        status_row.addWidget(status_indicator)
        
        # Node ID
        id_label = QLabel(f"ID: {self.node_id}")
        id_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: {APNTheme.COLORS['text_secondary']};
            }}
        """)
        status_row.addWidget(id_label)
        status_row.addStretch()
        
        layout.addLayout(status_row)
        
        # Details
        if self.details:
            for key, value in self.details.items():
                detail_row = QHBoxLayout()
                
                key_label = QLabel(f"{key}:")
                key_label.setStyleSheet(f"""
                    QLabel {{
                        font-weight: 500;
                        color: {APNTheme.COLORS['text_secondary']};
                        min-width: 80px;
                    }}
                """)
                
                value_label = QLabel(str(value))
                value_label.setStyleSheet(f"""
                    QLabel {{
                        color: {APNTheme.COLORS['text_primary']};
                    }}
                """)
                
                detail_row.addWidget(key_label)
                detail_row.addWidget(value_label)
                detail_row.addStretch()
                
                layout.addLayout(detail_row)
        
        return widget


class HolographicHeader(QWidget):
    """Holographic header with logo and title"""
    
    def __init__(self, title="Alpha Protocol Network", subtitle="", parent=None):
        super().__init__(parent)
        self.title = title
        self.subtitle = subtitle
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup header UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Logo (Alpha symbol)
        logo = QLabel("Α")
        logo.setStyleSheet(f"""
            QLabel {{
                font-size: 48px;
                font-weight: 700;
                color: {APNTheme.COLORS['alpha_gold']};
                border: 2px solid {APNTheme.COLORS['alpha_gold']};
                border-radius: 12px;
                padding: 16px;
                min-width: 80px;
                max-width: 80px;
                text-align: center;
                background: {APNTheme.COLORS['glass_primary']};
            }}
        """)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        # Title and subtitle
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(self.title)
        title_label.setProperty("class", "title")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                font-weight: 700;
                color: {APNTheme.COLORS['alpha_gold']};
                margin: 0px;
            }}
        """)
        text_layout.addWidget(title_label)
        
        if self.subtitle:
            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 16px;
                    font-weight: 400;
                    color: {APNTheme.COLORS['text_secondary']};
                    margin: 0px;
                }}
            """)
            text_layout.addWidget(subtitle_label)
            
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Add glow effect
        glow = GlowEffect(QColor(255, 215, 0, 50), 30)
        self.setGraphicsEffect(glow)


class MetricsGrid(QWidget):
    """Grid layout for displaying multiple metrics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        
    def add_metric(self, title, value, unit="", trend=None, row=0, col=0):
        """Add a metric card to the grid"""
        metric_card = MetricCard(title, value, unit, trend)
        self.grid_layout.addWidget(metric_card, row, col)
        return metric_card
    
    def add_custom_widget(self, widget, row=0, col=0, row_span=1, col_span=1):
        """Add a custom widget to the grid"""
        self.grid_layout.addWidget(widget, row, col, row_span, col_span)
