import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
import meshtastic.serial_interface
from pubsub import pub
import logging

class MeshtasticService(QObject):
    new_message = pyqtSignal(str)
    update_nodes = pyqtSignal(dict)
    iface = None

    @classmethod
    def sendText(cls, text):
        logger = logging.getLogger("MeshtasticService")
        if cls.iface is None:
            logger.error("Meshtastic iface not initialized. Cannot send message.")
            return False
        try:
            logger.info(f"Broadcasting via mesh: {text}")
            cls.iface.sendText(text)
            logger.info("Broadcast successful.")
            return True
        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return False

    def __init__(self):
        super().__init__()

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        # ✅ Only run this AFTER QApplication exists!
        # Use auto-detection like the original working version
        try:
            MeshtasticService.iface = meshtastic.serial_interface.SerialInterface()
            pub.subscribe(self._on_receive, "meshtastic.receive")

            time.sleep(2)
            nodes = getattr(MeshtasticService.iface, "nodes", None)
            if nodes is not None:
                print(f"📊 Meshtastic: Found {len(nodes)} total nodes in database")
                
                # Count actually online nodes
                online_count = 0
                current_time = time.time()
                for node_id, node_info in nodes.items():
                    last_heard = node_info.get('lastHeard', 0)
                    if last_heard > 0:
                        time_since_heard = current_time - last_heard
                        # Consider online if heard from in last 30 minutes
                        if time_since_heard < 1800:  
                            online_count += 1
                
                print(f"📡 Meshtastic: {online_count} nodes active (heard in last 30 min)")
                print(f"🔍 Sample nodes: {list(nodes.keys())[:5]}")
                
                self.update_nodes.emit(nodes)
            else:
                self.update_nodes.emit({})
                print("⚠️ MeshtasticService.iface.nodes not available")

            while True:
                time.sleep(10)
                nodes = getattr(MeshtasticService.iface, "nodes", None)
                if nodes is not None:
                    # Only log periodically to avoid spam
                    import time as time_module
                    if not hasattr(self, '_last_log_time') or time_module.time() - self._last_log_time > 60:
                        online_count = sum(1 for node_info in nodes.values() 
                                         if node_info.get('lastHeard', 0) > time_module.time() - 1800)
                        print(f"🔄 Periodic update: {len(nodes)} total, {online_count} recently active")
                        self._last_log_time = time_module.time()
                    
                    self.update_nodes.emit(nodes)
                else:
                    self.update_nodes.emit({})
                    print("⚠️ MeshtasticService.iface.nodes not available")
        except Exception as e:
            print(f"❌ Failed to initialize Meshtastic interface: {e}")
            print("🔍 Make sure a Meshtastic device is connected via USB")
            # Emit empty nodes to prevent UI errors
            self.update_nodes.emit({})

    def _on_receive(self, packet):
        decoded = packet.get('decoded', {})
        portnum = decoded.get('portnum')
        if portnum == 'TEXT_MESSAGE_APP':
            payload = decoded.get('payload')
            try:
                text = payload if isinstance(payload, str) else payload.decode('utf-8')
            except Exception:
                text = "(undecodable)"
            sender = packet.get('fromId', 'unknown')
            msg = f"[{sender}] {text}"
            self.new_message.emit(msg)
