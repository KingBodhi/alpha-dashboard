"""
Alpha Protocol Network - Main Application Entry Point
Refactored to use proper async architecture with service separation.
"""
import sys
import asyncio
import threading
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Core APN imports
from core.config import APNConfig
from core.logging_config import setup_logging
from core.service_manager import ServiceManager

# GUI imports
from app.main_window import MainWindow

# Legacy compatibility
from app.pages import globals

# Global service manager instance
service_manager = None

def main():
    """Main application entry point"""
    # Setup logging
    logger = setup_logging("INFO")
    logger.info("Starting Alpha Protocol Network Dashboard")
    
    try:
        # Load configuration
        config = APNConfig.load()
        logger.info(f"Loaded configuration for node: {config.identity.node_id}")
        
        # Fix for QWebEngineView
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # For now, skip the background services to get the UI working
        # TODO: Re-implement service thread without signal handling issues
        
        # Start PyQt UI
        app = QApplication(sys.argv)
        window = MainWindow(config)
        window.show()
        
        # Start services after window is shown (like original)
        window.start_service()
        
        # Start the GUI event loop
        exit_code = app.exec()
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Application startup error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
