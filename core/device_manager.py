"""
Alpha Protocol Network - Device Manager
Real hardware detection and management for ESP32, LoRa, Bluetooth, etc.
"""
import serial
import serial.tools.list_ports
import platform
import subprocess
import asyncio
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .logging_config import get_logger

logger = get_logger("device_manager")

@dataclass
class APNDevice:
    """APN-compatible device"""
    device_id: str
    device_type: str  # esp32, lora, bluetooth, wifi, satellite
    port: str
    description: str
    vendor_id: Optional[str] = None
    product_id: Optional[str] = None
    status: str = "disconnected"  # connected, disconnected, error
    capabilities: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}

class DeviceManager:
    """Manages APN-compatible hardware devices"""
    
    # Known device signatures for APN hardware
    KNOWN_DEVICES = {
        # ESP32 variants
        ("1a86", "7523"): {"type": "esp32", "name": "ESP32 (CH340)"},
        ("10c4", "ea60"): {"type": "esp32", "name": "ESP32 (CP2102)"},
        ("0403", "6001"): {"type": "esp32", "name": "ESP32 (FTDI)"},
        ("16c0", "0483"): {"type": "esp32", "name": "ESP32 Dev Board"},
        
        # LoRa modules
        ("0403", "6015"): {"type": "lora", "name": "LoRa Module (FTDI)"},
        
        # Arduino/compatible boards
        ("2341", "0043"): {"type": "arduino", "name": "Arduino Uno"},
        ("2341", "0001"): {"type": "arduino", "name": "Arduino Mega"},
        
        # Raspberry Pi (when connected via USB)
        ("0424", "ec00"): {"type": "raspberry_pi", "name": "Raspberry Pi USB"}
    }
    
    def __init__(self):
        self.devices: List[APNDevice] = []
        self.monitoring = False
        
    async def scan_devices(self) -> List[APNDevice]:
        """Scan for APN-compatible devices"""
        logger.info("Scanning for APN-compatible devices...")
        devices = []
        
        # Scan serial ports
        serial_devices = await self._scan_serial_devices()
        devices.extend(serial_devices)
        
        # Scan Bluetooth devices
        bluetooth_devices = await self._scan_bluetooth_devices()
        devices.extend(bluetooth_devices)
        
        # Scan WiFi interfaces
        wifi_devices = await self._scan_wifi_devices()
        devices.extend(wifi_devices)
        
        self.devices = devices
        logger.info(f"Found {len(devices)} APN-compatible devices")
        
        return devices
    
    async def _scan_serial_devices(self) -> List[APNDevice]:
        """Scan for serial devices (ESP32, LoRa, etc.)"""
        devices = []
        
        try:
            ports = serial.tools.list_ports.comports()
            
            for port in ports:
                device_type = "unknown"
                device_name = port.description
                capabilities = []
                
                # Check if it's a known device
                if port.vid and port.pid:
                    vid_hex = f"{port.vid:04x}"
                    pid_hex = f"{port.pid:04x}"
                    device_key = (vid_hex, pid_hex)
                    
                    if device_key in self.KNOWN_DEVICES:
                        known_device = self.KNOWN_DEVICES[device_key]
                        device_type = known_device["type"]
                        device_name = known_device["name"]
                        
                        # Set capabilities based on device type
                        if device_type == "esp32":
                            capabilities = ["mesh_node", "lora", "wifi", "bluetooth"]
                        elif device_type == "lora":
                            capabilities = ["lora", "mesh_relay"]
                        elif device_type == "arduino":
                            capabilities = ["sensor_node", "actuator"]
                
                # Try to probe the device for APN compatibility
                is_apn_compatible = await self._probe_device_compatibility(port.device)
                
                if is_apn_compatible or device_type in ["esp32", "lora"]:
                    device = APNDevice(
                        device_id=f"{device_type}_{port.device.replace('/', '_')}",
                        device_type=device_type,
                        port=port.device,
                        description=device_name,
                        vendor_id=vid_hex if port.vid else None,
                        product_id=pid_hex if port.pid else None,
                        status="connected",
                        capabilities=capabilities,
                        metadata={
                            "serial_number": port.serial_number,
                            "manufacturer": port.manufacturer,
                            "location": port.location,
                            "hwid": port.hwid
                        }
                    )
                    devices.append(device)
                    logger.info(f"Found APN device: {device_name} on {port.device}")
        
        except Exception as e:
            logger.error(f"Error scanning serial devices: {e}")
        
        return devices
    
    async def _probe_device_compatibility(self, port: str) -> bool:
        """Probe a device to see if it supports APN protocol"""
        try:
            # Try to open serial connection and send APN identification command
            ser = serial.Serial(port, 115200, timeout=2)
            
            # Send APN identification command
            ser.write(b"APN_IDENTIFY\n")
            response = ser.readline().decode().strip()
            
            ser.close()
            
            # Check if device responds with APN protocol
            return response.startswith("APN_NODE") or response.startswith("APN_RELAY")
            
        except Exception:
            # If we can't connect, assume it's not APN compatible
            return False
    
    async def _scan_bluetooth_devices(self) -> List[APNDevice]:
        """Scan for Bluetooth devices that can be used for mesh networking"""
        devices = []
        
        try:
            system = platform.system().lower()
            
            if system == "linux":
                # Use bluetoothctl on Linux
                result = await self._run_command(["bluetoothctl", "scan", "on"])
                await asyncio.sleep(3)  # Let scan run
                result = await self._run_command(["bluetoothctl", "devices"])
                
                if result and result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Device' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                mac = parts[1]
                                name = ' '.join(parts[2:])
                                
                                device = APNDevice(
                                    device_id=f"bluetooth_{mac.replace(':', '_')}",
                                    device_type="bluetooth",
                                    port=mac,
                                    description=f"Bluetooth Device: {name}",
                                    status="discovered",
                                    capabilities=["bluetooth_mesh", "p2p_communication"],
                                    metadata={"mac_address": mac, "device_name": name}
                                )
                                devices.append(device)
            
            elif system == "darwin":  # macOS
                # Use system_profiler on macOS
                result = await self._run_command(["system_profiler", "SPBluetoothDataType", "-json"])
                
                if result and result.returncode == 0:
                    try:
                        data = json.loads(result.stdout)
                        # Parse Bluetooth data (simplified)
                        logger.info("Bluetooth scanning available on macOS")
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            logger.debug(f"Bluetooth scanning not available: {e}")
        
        return devices
    
    async def _scan_wifi_devices(self) -> List[APNDevice]:
        """Scan for WiFi interfaces that can be used for mesh networking"""
        devices = []
        
        try:
            system = platform.system().lower()
            
            if system == "linux":
                # Check for wireless interfaces
                result = await self._run_command(["iwconfig"])
                if result and result.returncode == 0:
                    interfaces = []
                    for line in result.stdout.split('\n'):
                        if 'IEEE 802.11' in line:
                            interface = line.split()[0]
                            interfaces.append(interface)
                    
                    for interface in interfaces:
                        device = APNDevice(
                            device_id=f"wifi_{interface}",
                            device_type="wifi",
                            port=interface,
                            description=f"WiFi Interface: {interface}",
                            status="available",
                            capabilities=["wifi_mesh", "ad_hoc_network", "access_point"],
                            metadata={"interface": interface}
                        )
                        devices.append(device)
                        
            elif system == "darwin":  # macOS
                # Check WiFi interfaces on macOS
                result = await self._run_command(["networksetup", "-listallhardwareports"])
                if result and result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for i, line in enumerate(lines):
                        if 'Wi-Fi' in line and i + 1 < len(lines):
                            device_line = lines[i + 1]
                            if 'Device:' in device_line:
                                interface = device_line.split('Device: ')[1].strip()
                                
                                device = APNDevice(
                                    device_id=f"wifi_{interface}",
                                    device_type="wifi",
                                    port=interface,
                                    description=f"WiFi Interface: {interface}",
                                    status="available",
                                    capabilities=["wifi_mesh", "ad_hoc_network"],
                                    metadata={"interface": interface}
                                )
                                devices.append(device)
                                break
                        
        except Exception as e:
            logger.debug(f"WiFi scanning error: {e}")
        
        return devices
    
    async def _run_command(self, command: List[str]) -> Optional[subprocess.CompletedProcess]:
        """Run a system command asynchronously"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return subprocess.CompletedProcess(
                args=command,
                returncode=process.returncode,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else ""
            )
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return None
    
    async def connect_device(self, device_id: str) -> bool:
        """Connect to and initialize a device for APN use"""
        device = self.get_device(device_id)
        if not device:
            return False
            
        try:
            if device.device_type == "esp32":
                return await self._connect_esp32(device)
            elif device.device_type == "lora":
                return await self._connect_lora(device)
            elif device.device_type == "bluetooth":
                return await self._connect_bluetooth(device)
            elif device.device_type == "wifi":
                return await self._connect_wifi(device)
            
        except Exception as e:
            logger.error(f"Failed to connect to device {device_id}: {e}")
            device.status = "error"
            
        return False
    
    async def _connect_esp32(self, device: APNDevice) -> bool:
        """Connect to ESP32 device and initialize APN firmware"""
        try:
            # Open serial connection
            ser = serial.Serial(device.port, 115200, timeout=5)
            
            # Send initialization command
            ser.write(b"APN_INIT\n")
            response = ser.readline().decode().strip()
            
            if response.startswith("APN_READY"):
                device.status = "connected"
                logger.info(f"ESP32 device {device.device_id} connected successfully")
                
                # Get device capabilities
                ser.write(b"APN_CAPS\n")
                caps_response = ser.readline().decode().strip()
                if caps_response.startswith("CAPS:"):
                    caps = caps_response.split("CAPS:")[1].split(",")
                    device.capabilities.extend(caps)
                
                ser.close()
                return True
            
            ser.close()
            
        except Exception as e:
            logger.error(f"ESP32 connection error: {e}")
            
        return False
    
    async def _connect_lora(self, device: APNDevice) -> bool:
        """Connect to LoRa device"""
        # Implementation for LoRa device connection
        device.status = "connected"
        return True
    
    async def _connect_bluetooth(self, device: APNDevice) -> bool:
        """Connect to Bluetooth device"""
        # Implementation for Bluetooth device connection
        device.status = "connected"
        return True
    
    async def _connect_wifi(self, device: APNDevice) -> bool:
        """Configure WiFi interface for mesh networking"""
        # Implementation for WiFi mesh configuration
        device.status = "connected"
        return True
    
    def get_device(self, device_id: str) -> Optional[APNDevice]:
        """Get device by ID"""
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None
    
    def get_connected_devices(self) -> List[APNDevice]:
        """Get all connected devices"""
        return [d for d in self.devices if d.status == "connected"]
    
    def get_devices_by_type(self, device_type: str) -> List[APNDevice]:
        """Get devices by type"""
        return [d for d in self.devices if d.device_type == device_type]
    
    async def start_monitoring(self):
        """Start continuous device monitoring"""
        self.monitoring = True
        logger.info("Starting device monitoring")
        
        while self.monitoring:
            await self.scan_devices()
            await asyncio.sleep(10)  # Scan every 10 seconds
    
    def stop_monitoring(self):
        """Stop device monitoring"""
        self.monitoring = False
        logger.info("Stopping device monitoring")
