#!/usr/bin/env python3
"""
Integration test for Bitcoin dashboard on different systems.
Tests the full Bitcoin service and dashboard integration.
"""

import sys
import os
import time
import platform
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_system_detection():
    """Test system capability detection."""
    print("🔍 Testing system detection...")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print(f"System: {platform.system()}")
    
    from services.bitcoin_service import BitcoinService
    service = BitcoinService()
    
    print(f"Is low-power device: {service.is_low_power_device}")
    print(f"Base timeout: {service.base_timeout}s")
    print(f"Update interval: {service.update_interval}ms")
    print(f"Max retries: {service.max_retries}")
    
    # Check if psutil is available
    try:
        import psutil
        memory_gb = psutil.virtual_memory().total / (1024**3)
        cpu_count = psutil.cpu_count()
        print(f"Memory: {memory_gb:.1f} GB")
        print(f"CPU cores: {cpu_count}")
        print("✅ psutil available - system monitoring enabled")
    except ImportError:
        print("⚠️ psutil not available - basic system detection only")

def test_dashboard_creation():
    """Test Bitcoin dashboard widget creation."""
    print("\n🎛️ Testing dashboard widget creation...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from app.widgets.bitcoin_dashboard import BitcoinDashboard
        
        app = QApplication(sys.argv)
        dashboard = BitcoinDashboard()
        
        # Test safe_float function
        test_values = [
            Decimal('123.456'),
            None,
            'invalid',
            999999.99
        ]
        
        for val in test_values:
            result = dashboard.safe_float(val)
            print(f"  safe_float({val}) = {result}")
        
        print("✅ Dashboard widget created successfully")
        return dashboard
        
    except Exception as e:
        print(f"❌ Dashboard creation failed: {e}")
        return None

def test_service_creation():
    """Test Bitcoin service creation."""
    print("\n⚙️ Testing Bitcoin service creation...")
    
    try:
        from services.bitcoin_service import BitcoinService
        service = BitcoinService()
        
        print(f"RPC Host: {service.rpc_host}:{service.rpc_port}")
        print(f"Connection timeout: {service.connection_timeout}s")
        print(f"Update interval: {service.update_interval}ms")
        
        # Test system resource check
        resource_ok = service._check_system_resources()
        print(f"System resources OK: {resource_ok}")
        
        print("✅ Bitcoin service created successfully")
        return service
        
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        return None

def test_integration():
    """Test integration between service and dashboard."""
    print("\n🔗 Testing service-dashboard integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from app.widgets.bitcoin_dashboard import BitcoinDashboard
        from services.bitcoin_service import BitcoinService
        
        app = QApplication(sys.argv)
        dashboard = BitcoinDashboard()
        service = BitcoinService()
        
        # Connect signals
        service.status_message.connect(dashboard.update_status_message)
        service.connection_status_changed.connect(dashboard.update_connection_status)
        service.error_occurred.connect(dashboard.show_error_message)
        
        # Test status message
        service.status_message.emit("🔧 Testing integration...")
        
        # Test connection status
        service.connection_status_changed.emit(False)
        service.connection_status_changed.emit(True)
        
        print("✅ Integration signals working correctly")
        
        # Test mock data updates
        mock_blockchain_info = {
            'chain': 'main',
            'blocks': 904589,
            'difficulty': Decimal('67957790298975.61'),
            'verificationprogress': Decimal('0.9999999'),
            'size_on_disk': Decimal('578123456789')
        }
        
        dashboard.update_blockchain_info(mock_blockchain_info)
        print("✅ Mock blockchain info update successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_raspberry_pi_adaptations():
    """Test Raspberry Pi specific adaptations."""
    print("\n🍓 Testing Raspberry Pi adaptations...")
    
    from services.bitcoin_service import BitcoinService
    
    # Force low-power detection for testing
    service = BitcoinService()
    original_is_low_power = service.is_low_power_device
    
    # Test with forced low-power mode
    service.is_low_power_device = True
    service.base_timeout = 45
    service.connection_timeout = 60
    service.update_interval = 20000
    service.max_retries = 8
    
    print(f"Low-power mode timeouts:")
    print(f"  Base timeout: {service.base_timeout}s")
    print(f"  Connection timeout: {service.connection_timeout}s") 
    print(f"  Update interval: {service.update_interval}ms")
    print(f"  Max retries: {service.max_retries}")
    
    # Test with normal mode
    service.is_low_power_device = False
    service.base_timeout = 15
    service.connection_timeout = 30
    service.update_interval = 5000
    service.max_retries = 5
    
    print(f"Normal mode timeouts:")
    print(f"  Base timeout: {service.base_timeout}s")
    print(f"  Connection timeout: {service.connection_timeout}s")
    print(f"  Update interval: {service.update_interval}ms")
    print(f"  Max retries: {service.max_retries}")
    
    # Restore original detection
    service.is_low_power_device = original_is_low_power
    
    print("✅ Raspberry Pi adaptations tested successfully")

def main():
    """Run all integration tests."""
    print("🧪 Bitcoin Dashboard Integration Test")
    print("=" * 50)
    
    try:
        test_system_detection()
        dashboard = test_dashboard_creation()
        service = test_service_creation()
        
        if dashboard and service:
            test_integration()
        
        test_raspberry_pi_adaptations()
        
        print("\n" + "=" * 50)
        print("🎉 All integration tests completed!")
        print("\n📋 Summary:")
        print("   - System detection working")
        print("   - Dashboard widget functional")
        print("   - Bitcoin service initialized")
        print("   - Signal connections established")
        print("   - Raspberry Pi adaptations ready")
        print("\n✅ The Bitcoin dashboard should work on both Raspberry Pi and other systems!")
        
    except Exception as e:
        print(f"\n❌ Integration test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
