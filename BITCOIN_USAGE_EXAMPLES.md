# Bitcoin Integration Usage Examples

This document provides practical examples of using the Bitcoin integration in the Alpha Dashboard.

## Quick Start

1. **Start the dashboard:**
   ```bash
   python3 main.py
   ```

2. **Navigate to Bitcoin page:**
   - Click "Bitcoin" in the left sidebar

3. **Configure connection (if needed):**
   - Click "Settings" button
   - Enter your Bitcoin Core RPC credentials
   - Click "Test Connection" to verify
   - Click "Save"

4. **Connect to Bitcoin node:**
   - Click "Connect" button
   - Watch real-time blockchain data appear

## Example Bitcoin Core Configuration

Add these lines to your `bitcoin.conf` file (usually in `~/.bitcoin/bitcoin.conf`):

```ini
# Enable RPC server
server=1

# RPC credentials
rpcuser=admin
rpcpassword=admin123

# Allow local connections
rpcallowip=127.0.0.1

# RPC port (default is 8332 for mainnet)
rpcport=8332

# Optional: Performance improvements
dbcache=2048
maxconnections=125

# Optional: Enable transaction index for full functionality
txindex=1
```

## Example Usage Scenarios

### Monitoring Block Production

The dashboard automatically shows new blocks as they arrive:

```
🔗 New block: 123456789abcdef... (Height: 750000)
```

You can double-click any block in the "Recent Blocks" tab to view full details including all transactions.

### Network Health Monitoring

Check the "Network" tab to monitor:
- Number of connected peers
- Protocol versions
- Network activity status
- Mempool size and congestion

### Development and Testing

For developers working with testnet or regtest:

1. **Testnet configuration:**
   ```ini
   testnet=1
   rpcport=18332
   ```

2. **Regtest configuration:**
   ```ini
   regtest=1
   rpcport=18443
   ```

3. **Update dashboard settings:**
   - Click "Settings" in Bitcoin dashboard
   - Change port to 18332 (testnet) or 18443 (regtest)
   - Click "Test Connection" and "Save"

### Custom Update Intervals

Adjust update frequency based on your needs:

- **High frequency (real-time):** 1000ms (1 second)
- **Normal (default):** 5000ms (5 seconds)  
- **Low frequency (conserve resources):** 30000ms (30 seconds)

## Integration with Other Services

The Bitcoin service can be extended to work with other dashboard components:

### Home Page Summary

The home page automatically shows:
- Connection status (🟢/⚫)
- Current block height
- Network type (mainnet/testnet/regtest)
- Number of peers

### API Integration

Access Bitcoin data programmatically:

```python
# Get reference to Bitcoin service
bitcoin_service = main_window.bitcoin_service

# Check if connected
if bitcoin_service.is_connected:
    # Send custom RPC command
    result = bitcoin_service.send_raw_command('getpeerinfo')
    
    # Get specific block
    block = bitcoin_service.get_block_by_hash(block_hash)
    
    # Get transaction details
    tx = bitcoin_service.get_transaction(txid)
```

## Troubleshooting Common Issues

### Connection Refused
```
❌ Connection failed: [Errno 61] Connection refused
```
**Solutions:**
- Ensure Bitcoin Core is running
- Check that `server=1` is in bitcoin.conf
- Verify the port number (8332 for mainnet, 18332 for testnet)

### Authentication Failed
```
❌ RPC Error: Forbidden
```
**Solutions:**
- Check rpcuser and rpcpassword in bitcoin.conf
- Ensure they match dashboard settings
- Restart Bitcoin Core after changing bitcoin.conf

### Slow Updates
```
Dashboard seems sluggish or unresponsive
```
**Solutions:**
- Increase update interval in settings (e.g., 10000ms)
- Check Bitcoin Core sync status
- Reduce dbcache if system has low memory

### Missing Block Details
```
Double-clicking blocks shows minimal information
```
**Solutions:**
- Add `txindex=1` to bitcoin.conf for full transaction indexing
- Restart Bitcoin Core (will require full reindex)
- Allow time for indexing to complete

## Advanced Features

### Custom RPC Commands

Use the raw command interface for advanced operations:

```python
# Get wallet information (if wallet is loaded)
wallet_info = bitcoin_service.send_raw_command('getwalletinfo')

# Get mining information
mining_info = bitcoin_service.send_raw_command('getmininginfo')

# Get detailed mempool entry
mempool_entry = bitcoin_service.send_raw_command('getmempoolentry', txid)
```

### Monitoring Multiple Nodes

You can run multiple dashboard instances to monitor different Bitcoin nodes:

1. Copy the dashboard directory
2. Update bitcoin_config.py in each copy with different connection details
3. Run multiple instances on different ports

### Integration with Lightning Network

For Lightning Network monitoring, the Bitcoin backend provides the foundation. Consider extending with:

- LND REST API integration
- Channel monitoring
- Payment tracking
- Node management

## Security Considerations

### Production Use

For production environments:

1. **Use strong credentials:**
   ```ini
   rpcuser=production_user_$(openssl rand -hex 8)
   rpcpassword=$(openssl rand -hex 32)
   ```

2. **Restrict access:**
   ```ini
   rpcallowip=127.0.0.1
   rpcbind=127.0.0.1
   ```

3. **Consider cookie authentication:**
   ```ini
   # Remove rpcuser/rpcpassword and use cookie file instead
   rpccookiefile=/path/to/custom/cookie/file
   ```

### Network Security

- Never expose RPC port to the internet
- Use VPN for remote access
- Consider SSH tunneling for remote monitoring
- Regular security updates for Bitcoin Core

## Performance Optimization

### Resource Usage

Monitor and optimize:

- **CPU usage:** Adjust update intervals
- **Memory usage:** Configure Bitcoin Core dbcache
- **Network usage:** Limit peer connections if on metered connection
- **Disk I/O:** Use SSD for Bitcoin Core data directory

### Large Blockchains

For nodes with large blockchain data:

- Increase Bitcoin Core timeouts
- Use pruned nodes if historical data isn't needed
- Consider running on dedicated hardware
- Monitor disk space regularly
