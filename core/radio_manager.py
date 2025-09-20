"""
Alpha Protocol Network - Radio Manager
Abstraction layer for different radio types with device discovery.
"""
import asyncio
import glob
import platform
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .logging_config import get_logger

logger = get_logger("radio_manager")

@dataclass
class RadioDevice:
    """Radio device information"""
    device_id: str
    device_path: str
    radio_type: str
    status: str  # connected, disconnected, error
    metadata: Dict[str, Any]

@dataclass  
class RadioMessage:
    """Standard radio message format"""
    source_id: str
    dest_id: str = "broadcast"
    message_type: str = "text"
    payload: bytes = b""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class RadioInterface(ABC):
    """Abstract base class for radio interfaces"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the radio interface"""
        pass
    
    @abstractmethod
    async def send_message(self, message: RadioMessage) -> bool:
        """Send a message via this radio"""
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[RadioMessage]:
        """Receive pending messages"""
        pass
    
    @abstractmethod
    async def get_device_info(self) -> RadioDevice:
        """Get device information"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Clean disconnect"""
        pass

class MeshtasticInterface(RadioInterface):
    """Meshtastic radio interface with auto-discovery"""
    
    def __init__(self, device_path: str = "auto"):
        self.device_path = device_path
        self.interface = None
        self.connected = False
        
    async def initialize(self) -> bool:
        """Initialize Meshtastic connection with auto-discovery"""
        try:
            import meshtastic.serial_interface
            from pubsub import pub
            
            # Auto-discover device if needed
            if self.device_path == "auto":
                discovered_path = await self.discover_device()
                if not discovered_path:
                    logger.error("No Meshtastic devices found")
                    return False
                self.device_path = discovered_path
            
            logger.info(f"Connecting to Meshtastic device at {self.device_path}")
            
            # Connect to device
            self.interface = meshtastic.serial_interface.SerialInterface(
                devPath=self.device_path
            )
            
            # Subscribe to incoming messages
            pub.subscribe(self._on_receive, "meshtastic.receive")
            
            self.connected = True
            logger.info("Meshtastic interface initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Meshtastic interface: {e}")
            return False
    
    async def discover_device(self) -> Optional[str]:
        """Discover Meshtastic devices"""
        system = platform.system().lower()
        
        if system == "linux":
            patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/serial/by-id/*"]
        elif system == "darwin":  # macOS
            patterns = ["/dev/tty.usbserial*", "/dev/tty.SLAB_USBtoUART*"]
        elif system == "windows":
            patterns = ["COM*"]
        else:
            logger.warning(f"Unsupported platform for auto-discovery: {system}")
            return None
        
        devices = []
        for pattern in patterns:
            devices.extend(glob.glob(pattern))
        
        if devices:
            logger.info(f"Found potential devices: {devices}")
            return devices[0]  # Return first found device
        
        return None
    
    async def send_message(self, message: RadioMessage) -> bool:
        """Send message via Meshtastic"""
        if not self.connected or not self.interface:
            logger.error("Meshtastic interface not connected")
            return False
        
        try:
            if message.message_type == "text":
                text = message.payload.decode('utf-8')
                self.interface.sendText(text, message.dest_id)
                logger.debug(f"Sent text message: {text}")
                return True
            else:
                logger.warning(f"Unsupported message type: {message.message_type}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def receive_messages(self) -> List[RadioMessage]:
        """Receive messages (handled by pubsub callback)"""
        # Messages are handled via pubsub in _on_receive
        return []
    
    def _on_receive(self, packet):
        """Handle incoming Meshtastic message"""
        try:
            decoded = packet.get('decoded', {})
            portnum = decoded.get('portnum')
            
            if portnum == 'TEXT_MESSAGE_APP':
                payload = decoded.get('payload')
                sender = packet.get('fromId', 'unknown')
                
                if isinstance(payload, bytes):
                    text = payload.decode('utf-8', errors='ignore')
                else:
                    text = str(payload)
                
                message = RadioMessage(
                    source_id=sender,
                    message_type="text",
                    payload=text.encode('utf-8'),
                    metadata={"rssi": packet.get('rssi', 0)}
                )
                
                # Emit message event for UI
                asyncio.create_task(self._emit_message(message))
                
        except Exception as e:
            logger.error(f"Error processing received message: {e}")
    
    async def _emit_message(self, message: RadioMessage):
        """Emit message to event system"""
        # This will be connected to the event bus
        logger.info(f"Received message from {message.source_id}: {message.payload.decode()}")
    
    async def get_device_info(self) -> RadioDevice:
        """Get device information"""
        return RadioDevice(
            device_id=f"meshtastic_{self.device_path}",
            device_path=self.device_path,
            radio_type="meshtastic",
            status="connected" if self.connected else "disconnected",
            metadata={"interface": "serial"}
        )
    
    async def disconnect(self):
        """Disconnect from device"""
        if self.interface:
            try:
                self.interface.close()
            except:
                pass
        self.connected = False
        logger.info("Meshtastic interface disconnected")

class RadioManager:
    """Manages multiple radio interfaces"""
    
    def __init__(self):
        self.interfaces: Dict[str, RadioInterface] = {}
        self.active_radios: List[str] = []
        
    async def initialize_radio(self, radio_type: str, config: Dict[str, Any]) -> bool:
        """Initialize a specific radio type"""
        try:
            if radio_type == "meshtastic":
                device_path = config.get("device_path", "auto")
                interface = MeshtasticInterface(device_path)
                
            else:
                logger.error(f"Unsupported radio type: {radio_type}")
                return False
            
            if await interface.initialize():
                self.interfaces[radio_type] = interface
                self.active_radios.append(radio_type)
                logger.info(f"Radio {radio_type} initialized successfully")
                return True
            else:
                logger.error(f"Failed to initialize radio {radio_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing radio {radio_type}: {e}")
            return False
    
    async def send_message(self, message: RadioMessage, radio_types: List[str] = None) -> bool:
        """Send message via specified radios or all active radios"""
        if radio_types is None:
            radio_types = self.active_radios
        
        success_count = 0
        for radio_type in radio_types:
            if radio_type in self.interfaces:
                if await self.interfaces[radio_type].send_message(message):
                    success_count += 1
        
        return success_count > 0
    
    async def get_active_devices(self) -> List[RadioDevice]:
        """Get information about all active radio devices"""
        devices = []
        for interface in self.interfaces.values():
            device = await interface.get_device_info()
            devices.append(device)
        return devices
    
    async def shutdown(self):
        """Shutdown all radio interfaces"""
        for interface in self.interfaces.values():
            await interface.disconnect()
        self.interfaces.clear()
        self.active_radios.clear()
        logger.info("All radio interfaces shut down")
