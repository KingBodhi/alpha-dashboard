from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from app.widgets.bitcoin_dashboard import BitcoinDashboard


class BitcoinPage(QWidget):
    """Bitcoin page containing the Bitcoin dashboard."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        # Create scrollable container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Create main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.addWidget(scroll_area)
        
        # Create Bitcoin dashboard
        self.bitcoin_dashboard = BitcoinDashboard()
        scroll_area.setWidget(self.bitcoin_dashboard)
        
    def get_dashboard(self):
        """Get reference to the Bitcoin dashboard widget."""
        return self.bitcoin_dashboard
