#!/usr/bin/env python3
"""
Bitcoin Core Connection Troubleshooter
This tool helps diagnose and fix persistent RPC connection issues.
"""

import sys
import os
import time
import socket

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_connection_issues():
    """Diagnose why Bitcoin Core RPC connections keep failing."""
    print("🔧 Bitcoin Core Connection Troubleshooter")
    print("=" * 60)
    
    # 1. Check Bitcoin Core configuration
    print("1️⃣ Checking Bitcoin Core Configuration...")
    try:
        from app.config.bitcoin_config import BITCOIN_RPC_CONFIG
        
        host = BITCOIN_RPC_CONFIG['rpc_host']
        port = BITCOIN_RPC_CONFIG['rpc_port']
        user = BITCOIN_RPC_CONFIG['rpc_user']
        # Don't print password for security
        
        print(f"   Host: {host}")
        print(f"   Port: {port}")
        print(f"   User: {user}")
        print(f"   Password: {'*' * len(BITCOIN_RPC_CONFIG.get('rpc_password', ''))}")
        
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        return
    
    # 2. Test network connectivity
    print(f"\n2️⃣ Testing Network Connectivity...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print(f"   ✅ Can connect to {host}:{port}")
        else:
            print(f"   ❌ Cannot connect to {host}:{port}")
            print(f"   Error code: {result}")
            
    except Exception as e:
        print(f"   ❌ Network test failed: {e}")
    
    # 3. Test Bitcoin Core RPC
    print(f"\n3️⃣ Testing Bitcoin Core RPC...")
    try:
        from bitcoinrpc.authproxy import AuthServiceProxy
        
        rpc_url = f"http://{user}:{BITCOIN_RPC_CONFIG['rpc_password']}@{host}:{port}/"
        
        # Test with very short timeout first
        rpc = AuthServiceProxy(rpc_url, timeout=5)
        
        start_time = time.time()
        try:
            block_count = rpc.getblockcount()
            elapsed = time.time() - start_time
            print(f"   ✅ RPC call successful: {block_count:,} blocks ({elapsed:.2f}s)")
            
        except Exception as rpc_error:
            elapsed = time.time() - start_time
            error_str = str(rpc_error).lower()
            
            print(f"   ❌ RPC call failed after {elapsed:.2f}s")
            print(f"   Error: {rpc_error}")
            
            # Analyze the error
            if "connection refused" in error_str:
                print(f"   🔍 Analysis: Bitcoin Core is not running or RPC is disabled")
            elif "unauthorized" in error_str or "401" in error_str:
                print(f"   🔍 Analysis: Wrong RPC username/password")
            elif "timeout" in error_str or "request-sent" in error_str:
                print(f"   🔍 Analysis: Bitcoin Core is overloaded or very slow")
            elif "connection reset" in error_str:
                print(f"   🔍 Analysis: Network connectivity issues")
            else:
                print(f"   🔍 Analysis: Unknown RPC error")
                
    except Exception as e:
        print(f"   ❌ RPC setup failed: {e}")
    
    # 4. Check Bitcoin Core process
    print(f"\n4️⃣ Checking Bitcoin Core Process...")
    try:
        import subprocess
        
        # Check if bitcoind is running
        if sys.platform.startswith('win'):
            cmd = 'tasklist | findstr bitcoin'
        else:
            cmd = 'ps aux | grep bitcoin'
            
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if 'bitcoin' in result.stdout.lower():
            print(f"   ✅ Bitcoin Core process is running")
            # Show relevant lines
            lines = [line for line in result.stdout.split('\n') if 'bitcoin' in line.lower()]
            for line in lines[:3]:  # Show first 3 matches
                print(f"     {line.strip()}")
        else:
            print(f"   ❌ Bitcoin Core process not found")
            print(f"   💡 You need to start Bitcoin Core first!")
            
    except Exception as e:
        print(f"   ❌ Process check failed: {e}")
    
    # 5. Provide specific solutions
    print(f"\n🎯 SOLUTIONS FOR YOUR ISSUE:")
    print("=" * 40)
    
    print(f"\n🔧 If Bitcoin Core is not running:")
    print(f"   • Start Bitcoin Core application")
    print(f"   • Or start bitcoind daemon")
    print(f"   • Wait for initial sync to complete")
    
    print(f"\n🔧 If RPC credentials are wrong:")
    print(f"   • Check ~/.bitcoin/bitcoin.conf")
    print(f"   • Ensure rpcuser and rpcpassword are set")
    print(f"   • Update app/config/bitcoin_config.py to match")
    
    print(f"\n🔧 If Bitcoin Core is overloaded:")
    print(f"   • Wait for sync to complete")
    print(f"   • Increase timeout in dashboard")
    print(f"   • Reduce number of peers")
    print(f"   • Use pruned mode if disk space is limited")
    
    print(f"\n🔧 If connection keeps timing out:")
    print(f"   • Increase rpc timeout in bitcoin.conf:")
    print(f"     rpctimeout=120")
    print(f"   • Increase RPC work queue:")
    print(f"     rpcworkqueue=64")
    print(f"   • Reduce RPC threads if system is slow:")
    print(f"     rpcthreads=4")
    
    print(f"\n🔧 Quick fix for dashboard:")
    print(f"   • Increase timeout in bitcoin_service.py")
    print(f"   • Reduce update frequency")
    print(f"   • Disable address monitoring temporarily")

def create_bitcoin_conf_template():
    """Create a sample bitcoin.conf with optimized RPC settings."""
    print(f"\n📄 Sample bitcoin.conf for Dashboard:")
    print("=" * 40)
    
    conf_content = """# Bitcoin Core configuration for Alpha Dashboard
# Save this as ~/.bitcoin/bitcoin.conf (Linux/Mac) or %APPDATA%\\Bitcoin\\bitcoin.conf (Windows)

# RPC Settings
server=1
rpcuser=bitcoinrpc
rpcpassword=your_secure_password_here
rpcport=8332
rpcbind=127.0.0.1
rpcallowip=127.0.0.1

# Performance Settings for Dashboard
rpctimeout=120
rpcworkqueue=64
rpcthreads=8

# Optional: Reduce resource usage
maxconnections=10
dbcache=512

# Optional: Enable pruning to save disk space
# prune=550

# Optional: Faster sync with assumevalid
# assumevalid=<recent_block_hash>
"""
    
    print(conf_content)
    
    # Try to save template
    try:
        import platform
        home = os.path.expanduser("~")
        
        if platform.system() == "Windows":
            bitcoin_dir = os.path.join(os.environ.get('APPDATA', ''), 'Bitcoin')
        else:
            bitcoin_dir = os.path.join(home, '.bitcoin')
        
        conf_path = os.path.join(bitcoin_dir, 'bitcoin.conf.template')
        
        os.makedirs(bitcoin_dir, exist_ok=True)
        with open(conf_path, 'w') as f:
            f.write(conf_content)
            
        print(f"💾 Template saved to: {conf_path}")
        print(f"   Rename to bitcoin.conf and update password")
        
    except Exception as e:
        print(f"❌ Could not save template: {e}")

if __name__ == "__main__":
    diagnose_connection_issues()
    create_bitcoin_conf_template()
    
    print(f"\n🚨 IMMEDIATE ACTION NEEDED:")
    print(f"1. Ensure Bitcoin Core is running")
    print(f"2. Check bitcoin.conf has RPC settings") 
    print(f"3. Restart Bitcoin Core after config changes")
    print(f"4. Wait for sync to complete")
    print(f"5. Test connection with: bitcoin-cli getblockcount")
