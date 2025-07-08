# Bitcoin Integration for Alpha Dashboard

This dashboard now includes Bitcoin blockchain monitoring capabilities using RPC connections to a Bitcoin Core node.

## Features

- **Real-time blockchain monitoring**: Block height, difficulty, network stats
- **Network information**: Peer connections, protocol versions
- **Mempool tracking**: Transaction count and size
- **Recent blocks display**: View latest blocks with details
- **Peer information**: Connected peers with versions and connection times
- **Home page summary**: Quick Bitcoin status overview

## Setup Requirements

### 1. Bitcoin Core Node

You need a running Bitcoin Core node with RPC enabled. Add these settings to your `bitcoin.conf` file:

```
# RPC Settings
rpcuser=admin
rpcpassword=admin123
rpcallowip=127.0.0.1
rpcport=8332
server=1

# Optional: For better performance
dbcache=2048
maxconnections=125
```

### 2. Configuration

Update the connection settings in `app/config/bitcoin_config.py`:

```python
BITCOIN_RPC_CONFIG = {
    "rpc_user": "admin",
    "rpc_password": "admin123", 
    "rpc_host": "127.0.0.1",
    "rpc_port": 8332,
    "update_interval": 5000,  # Update interval in milliseconds
}
```

### 3. Test Connection

Run the test script to verify your Bitcoin node is accessible:

```bash
python test_bitcoin_connection.py
```

## Usage

### Navigation

1. Start the dashboard: `python main.py`
2. Navigate to the "Bitcoin" tab in the sidebar
3. Click "Connect" to establish connection to your Bitcoin node
4. View real-time blockchain data across multiple tabs

### Home Page Integration

The home page includes a Bitcoin summary widget showing:
- Connection status
- Current block height
- Network type (mainnet/testnet/regtest)
- Number of connected peers

### Full Bitcoin Dashboard

The dedicated Bitcoin page provides:

- **Blockchain Tab**: Detailed blockchain information including difficulty, verification progress, and disk usage
- **Network Tab**: Network protocol details and connection statistics  
- **Recent Blocks Tab**: List of recent blocks (double-click for detailed JSON view)
- **Peers Tab**: Information about connected Bitcoin peers

## API Integration

The Bitcoin service provides these signals for real-time updates:

- `connection_status_changed(bool)`: Connection state changes
- `blockchain_info_updated(dict)`: Blockchain statistics updates
- `new_block_received(dict)`: New block notifications
- `mempool_updated(dict)`: Mempool statistics updates
- `network_info_updated(dict)`: Network information updates
- `peer_info_updated(list)`: Peer connection updates
- `error_occurred(str)`: Error notifications

## Troubleshooting

### Connection Issues

1. **"Connection failed"**: Verify Bitcoin Core is running and RPC is enabled
2. **"RPC Error: Forbidden"**: Check rpcuser/rpcpassword match your bitcoin.conf
3. **"Connection refused"**: Verify rpcport and rpcallowip settings
4. **"Timeout"**: Check if Bitcoin Core is fully synced and responsive

### Performance

- The dashboard updates every 5 seconds by default
- Adjust `update_interval` in config for different refresh rates
- Large mempools may slow down updates temporarily

### Security Notes

- The RPC credentials are stored in plain text in the config file
- For production use, consider using Bitcoin Core's cookie authentication
- Restrict RPC access to localhost only (`rpcallowip=127.0.0.1`)

## Advanced Features

### Custom RPC Commands

The Bitcoin service supports raw RPC commands:

```python
result = bitcoin_service.send_raw_command('getblock', block_hash, 2)
```

### Block and Transaction Details

Double-click any block in the Recent Blocks tab to view full JSON details, including all transactions.

## Dependencies

The Bitcoin integration adds these dependencies:
- `python-bitcoinrpc`: Bitcoin RPC client library
- `fastapi`: For the existing web server (already included)

Install with: `pip install -r requirements.txt`
