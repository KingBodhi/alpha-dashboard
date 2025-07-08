import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
import meshtastic.serial_interface
from pubsub import pub

class MeshtasticService(QObject):
    new_message = pyqtSignal(str)
    update_nodes = pyqtSignal(dict)
    iface = None

    def __init__(self):
        super().__init__()

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        # ✅ Only run this AFTER QApplication exists!
        MeshtasticService.iface = meshtastic.serial_interface.SerialInterface(devPath="/dev/ttyUSB0")
        pub.subscribe(self._on_receive, "meshtastic.receive")

        time.sleep(2)
        self.update_nodes.emit(MeshtasticService.iface.nodes)

        while True:
            time.sleep(10)
            self.update_nodes.emit(MeshtasticService.iface.nodes)

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
