import sys
import subprocess
import requests
import time
import json
import threading
import os
from pathlib import Path
import stat
import re
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import Qt, QTimer
from app.pages import globals


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# Import your PyQt Main Window
from app.main_window import MainWindow


# ========= Paths =========
APN_DIR = Path.home() / ".apn"
NODE_CONFIG_PATH = APN_DIR / "node_config.json"
REGISTRY_PATH = APN_DIR / "registry.json"


if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

cloudflared_path = os.path.join(base_path, 'assets', 'cloudflared-linux-amd64')



# ========= FastAPI Starter =========
def start_fastapi_server():
    """
    Starts the FastAPI server in a subprocess if it's not already running.
    """
    try:
        # Check if already running
        print("🔎 Checking if FastAPI server is already running...")
        resp = requests.get("http://localhost:8000", timeout=2)
        if resp.status_code == 200:
            print("✅ FastAPI server already running.")
            return
    except Exception:
        pass

    # Not running, start it
    print("⚡️ Starting FastAPI server...")
    subprocess.Popen(
        ["uvicorn", "app.server.apn_server:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.DEVNULL,

        stderr=subprocess.STDOUT
    )
    time.sleep(2)  # Give server time to start

def start_cloudflared_and_show_url(window, cloudflared_path):
    print("forwarding port")

    # Ensure binary is executable
    if not os.access(cloudflared_path, os.X_OK):
        print("🔧 Adding execute permission to cloudflared binary...")
        st = os.stat(cloudflared_path)
        os.chmod(cloudflared_path, st.st_mode | stat.S_IEXEC)

    # Start the tunnel process
    process = subprocess.Popen(
    [cloudflared_path, "tunnel", "--url", "http://localhost:8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

    # Regex pattern to capture the public URL
    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")

    # Background thread to monitor output
    def read_output():
        for line in iter(process.stdout.readline, ''):
            print("[cloudflared]", line.strip())
            match = url_pattern.search(line)
            if match:
                public_url = match.group(0)
                print("HELLLLOOO PUBLIC URL" + public_url)
                globals.PUBLIC_WEB_URL = public_url
                # Show clickable popup in the main Qt thread
               
                break

    threading.Thread(target=read_output, daemon=True).start()




# ========= Auto-register With Peers =========
def auto_register_with_peers():
    """
    Reads registry.json and tries to register this node with all known peers.
    """
    try:
        # Load own config
        with NODE_CONFIG_PATH.open() as f:
            own_config = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load own config: {e}")
        return

    # Load known peers
    try:
        if REGISTRY_PATH.exists():
            with REGISTRY_PATH.open() as f:
                peers = json.load(f)
        else:
            peers = []
    except Exception as e:
        print(f"❌ Failed to load registry.json: {e}")
        return

    # Register with each peer
    for peer in peers:
        if peer.get("nodeId") == own_config.get("nodeId"):
            continue  # Don't register to self

        peer_ip = peer.get("ip", "localhost")
        url = f"http://{peer_ip}:8000/register"

        try:
            print(f"🔗 Registering with {url}")
            resp = requests.post(url, json=own_config, timeout=5)
            if resp.ok:
                print(f"✅ Registered with {peer.get('nodeId', peer_ip)}")
            else:
                print(f"⚠️ Failed to register with {peer.get('nodeId', peer_ip)}: {resp.status_code}")
        except Exception as e:
            print(f"⚠️ Could not reach {peer.get('nodeId', peer_ip)}: {e}")


# ========= App Startup =========
def main():
    # Fix for QWebEngineView!
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # Start FastAPI Server
    start_fastapi_server()

    # Auto-register with peers in background
    threading.Thread(target=auto_register_with_peers, daemon=True).start()

    # Start PyQt UI
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.start_service()
    start_cloudflared_and_show_url(window, cloudflared_path)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
