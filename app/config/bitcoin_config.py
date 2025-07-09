"""
Bitcoin configuration settings.
You can modify these settings to connect to your Bitcoin node.
"""

# Bitcoin RPC Configuration
BITCOIN_RPC_CONFIG = {
    "rpc_user": "admin",
    "rpc_password": "admin123", 
    "rpc_host": "127.0.0.1",
    "rpc_port": 8332,
    "update_interval": 10000,  # Update interval in milliseconds (10 seconds, reduced load)
}

# UI Configuration
UI_CONFIG = {
    "max_recent_blocks": 50,  # Maximum number of recent blocks to display
    "max_peers_display": 20,  # Maximum number of peers to display
}
