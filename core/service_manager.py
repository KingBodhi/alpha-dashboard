"""
Alpha Protocol Network - Service Manager
Manages all APN services with proper lifecycle and supervision.
"""
import asyncio
import signal
import sys
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from .config import APNConfig
from .logging_config import get_logger
from .radio_manager import RadioManager, RadioMessage
from .web_server import APNWebServer

logger = get_logger("service_manager")

class ServiceManager:
    """Central service manager for all APN components"""
    
    def __init__(self, config: APNConfig):
        self.config = config
        self.services = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Core services
        self.radio_manager = RadioManager()
        self.web_server = APNWebServer(config, self.radio_manager)
        
        # Service registry
        self.services = {
            'radio_manager': self.radio_manager,
            'web_server': self.web_server,
        }
        
    async def start(self):
        """Start all services"""
        logger.info("Starting APN Service Manager")
        
        try:
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start radio manager
            await self._start_radio_manager()
            
            # Start web server
            await self._start_web_server()
            
            self.running = True
            logger.info("All services started successfully")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            await self.shutdown()
            raise
    
    async def _start_radio_manager(self):
        """Initialize radio interfaces"""
        logger.info("Starting radio manager...")
        
        for radio_type in self.config.radio.enabled_radios:
            config = {}
            if radio_type == "meshtastic":
                config["device_path"] = self.config.radio.meshtastic_device
            
            success = await self.radio_manager.initialize_radio(radio_type, config)
            if not success:
                logger.warning(f"Failed to initialize radio: {radio_type}")
    
    async def _start_web_server(self):
        """Start the web server"""
        logger.info("Starting web server...")
        
        await self.web_server.start(
            host=self.config.network.api_host,
            port=self.config.network.api_port
        )
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        if not self.running:
            return
            
        logger.info("Shutting down APN services...")
        self.running = False
        
        # Shutdown services in reverse order
        try:
            await self.web_server.stop()
            await self.radio_manager.shutdown()
            logger.info("All services shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self.shutdown_event.set()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        radio_devices = await self.radio_manager.get_active_devices()
        
        return {
            "running": self.running,
            "node_id": self.config.identity.node_id,
            "radios": [
                {
                    "type": device.radio_type,
                    "status": device.status,
                    "device": device.device_path
                }
                for device in radio_devices
            ],
            "web_server": {
                "host": self.config.network.api_host,
                "port": self.config.network.api_port,
                "status": "running" if self.running else "stopped"
            },
            "services": {
                "relay": self.config.services.relay_enabled,
                "storage": self.config.services.storage_enabled,
                "compute": self.config.services.compute_enabled,
                "bridge": self.config.services.bridge_enabled,
            }
        }
    
    async def send_message(self, text: str, dest_id: str = "broadcast") -> bool:
        """Send a message via radio"""
        message = RadioMessage(
            source_id=self.config.identity.node_id,
            dest_id=dest_id,
            message_type="text",
            payload=text.encode('utf-8')
        )
        
        return await self.radio_manager.send_message(message)

@asynccontextmanager
async def create_service_manager(config_path: Optional[str] = None):
    """Context manager for service manager lifecycle"""
    config = APNConfig.load(config_path)
    manager = ServiceManager(config)
    
    try:
        yield manager
    finally:
        await manager.shutdown()

# CLI entry point
async def main():
    """Main entry point for headless APN node"""
    logger.info("Starting Alpha Protocol Network node...")
    
    async with create_service_manager() as manager:
        await manager.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
