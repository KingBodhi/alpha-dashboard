# Bitcoin Dashboard Optimization Guide

## Overview

The Alpha Dashboard is optimized to handle slow Bitcoin Core nodes gracefully, particularly when `scantxoutset` operations take 30+ seconds. This guide explains the optimizations and how they work.

## Performance Issues Diagnosed

Based on diagnostic testing, the main performance bottleneck is:
- **`scantxoutset` operations taking 54+ seconds** on some nodes
- All other RPC operations remain fast (sub-3ms)
- Node is not overloaded, just slow at UTXO scanning

## Optimization Features

### 1. Slow Address Detection & Throttling

The dashboard automatically detects when address balance checks are slow:
- **Detection threshold**: Operations taking >20 seconds are marked as "slow"
- **Throttling**: Slow addresses are updated every 15 minutes instead of every cycle
- **User feedback**: Performance status indicators show when addresses are throttled

### 2. Adaptive Update Frequency

The dashboard adjusts its update frequency based on node performance:
- **Normal mode**: Updates every 30 seconds
- **Busy node**: Progressively increases intervals up to 5 minutes
- **Failed operations**: Exponentially backs off with retry logic

### 3. Single Address Per Cycle

To prevent overwhelming busy nodes:
- Only one address is updated per monitoring cycle
- Addresses are rotated round-robin style
- Slow addresses are skipped until their 15-minute window expires

### 4. Enhanced Error Handling

Robust error handling for common "busy node" scenarios:
- Detects "Request-sent" and busy node errors
- Implements progressive timeouts (30s → 60s → 120s)
- Graceful fallbacks when operations timeout

## User Interface Indicators

### Wallet Widget Status

The Bitcoin wallet widget shows performance status:
- **Normal**: "📍 Ready to monitor address"
- **Slow node detected**: "⏱️ Slow node - updates every 15min"
- **Throttled**: "⏳ Throttled - next check in Xmin"

### Console Messages

Monitor console output for performance insights:
```
⚠️ SLOW scantxoutset: 54.2s - will reduce frequency for this address
⏳ Skipping slow address bc1qxy2k... (waiting 847s)
🔄 Updating slow address bc1qxy2k... (last update was 16.2 minutes ago)
```

## Configuration Recommendations

### For Slow Nodes

If your node consistently has slow `scantxoutset` operations:

1. **Increase timeouts** in `bitcoin_config.py`:
   ```python
   "default_timeout": 120,  # 2 minute timeout
   ```

2. **Use legacy wallets** when possible:
   - Legacy wallets use `listunspent` (fast)
   - Descriptor wallets require `scantxoutset` (slow)

3. **Reduce update frequency**:
   ```python
   "update_interval": 60000,  # 1 minute intervals
   ```

### For Fast Nodes

If your node performs well:
- Keep default settings (30s intervals)
- Monitor for any performance degradation
- Optimizations will still help during busy periods

## Diagnostic Tools

### validate_optimization.py
Tests the optimization features:
```bash
python validate_optimization.py
```

### diagnose_node_activity.py
Comprehensive node performance analysis:
```bash
python diagnose_node_activity.py
```

### simple_balance_check.py
Basic balance checking for busy nodes:
```bash
python simple_balance_check.py <bitcoin_address>
```

## Performance Metrics

After optimization, expect:
- **Fast addresses**: Sub-second balance updates
- **Slow addresses**: 15-minute update intervals
- **UI responsiveness**: Always responsive, never blocks
- **Error reduction**: Fewer timeout and busy-node errors

## Troubleshooting

### If dashboard appears unresponsive:
1. Check console for "SLOW scantxoutset" messages
2. Verify Bitcoin Core is not overloaded (use diagnostic tools)
3. Consider using legacy wallet format
4. Increase timeout settings

### If balance updates are too infrequent:
1. Check if address is marked as "slow"
2. Wait for 15-minute throttling window to expire
3. Use manual refresh button for immediate updates
4. Consider optimizing Bitcoin Core configuration

### If seeing many timeout errors:
1. Increase timeout values in configuration
2. Reduce concurrent operations
3. Check Bitcoin Core debug.log for issues
4. Consider restarting Bitcoin Core

## Technical Details

### Slow Address Tracking
```python
# Addresses taking >20s are tracked
if elapsed_time > 20:
    self._slow_scan_addresses[address] = time.time()

# Throttled for 15 minutes
if time_since_last < 900:  # 15 minutes
    return  # Skip this update
```

### Progressive Timeouts
```python
# Adaptive timeout based on operation type
timeout = 30   # Normal operations
timeout = 60   # Heavy operations  
timeout = 120  # Ultra-slow scantxoutset
```

### Error Detection
```python
# Detect busy node patterns
busy_indicators = ['busy', 'request-sent', 'timeout', 'loading block index']
if any(phrase in error_str for phrase in busy_indicators):
    # Handle as temporary busy state, not permanent error
```

## Best Practices

1. **Monitor performance status** in the wallet widget
2. **Use diagnostic tools** to understand your node's characteristics
3. **Be patient** with slow addresses - throttling is by design
4. **Use manual refresh** for immediate balance checks when needed
5. **Consider node optimization** if consistently slow

## Future Enhancements

Potential improvements being considered:
- Address-specific update intervals based on transaction frequency
- Alternative balance checking methods for descriptor wallets
- Node performance caching and prediction
- User-configurable throttling thresholds
