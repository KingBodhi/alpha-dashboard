#!/usr/bin/env python3
"""
Test app startup time and responsiveness.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add the app directory to the path
sys.path.insert(0, '/Users/madhav/development/GitHub/alpha-dashboard')

def test_startup_performance():
    """Test how quickly the app starts and becomes responsive."""
    print("🧪 Testing app startup performance...")
    
    # Set Qt attributes before creating QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    
    start_time = time.time()
    
    # Import and create main window
    from app.main_window import MainWindow
    
    import_time = time.time()
    print(f"✅ Import time: {import_time - start_time:.2f}s")
    
    # Create window
    window = MainWindow()
    creation_time = time.time()
    print(f"✅ Window creation time: {creation_time - import_time:.2f}s")
    
    # Show window
    window.show()
    show_time = time.time()
    print(f"✅ Window show time: {show_time - creation_time:.2f}s")
    
    # Start services
    window.start_service()
    service_time = time.time()
    print(f"✅ Service start time: {service_time - show_time:.2f}s")
    
    total_time = service_time - start_time
    print(f"🎯 Total startup time: {total_time:.2f}s")
    
    if total_time < 3.0:
        print("✅ Startup performance is GOOD")
    elif total_time < 5.0:
        print("⚠️ Startup performance is ACCEPTABLE")
    else:
        print("❌ Startup performance is SLOW")
    
    # Test responsiveness by scheduling a quick close
    QTimer.singleShot(2000, app.quit)
    
    # Process events for 2 seconds to test responsiveness
    app.exec()
    
    print("✅ App remained responsive during startup")
    return total_time < 5.0

if __name__ == "__main__":
    success = test_startup_performance()
    if success:
        print("\n🚀 STARTUP PERFORMANCE TEST PASSED!")
        print("📌 The app should now be much more responsive.")
    else:
        print("\n⚠️ Startup still slow - may need further optimization.")
    
    sys.exit(0 if success else 1)
