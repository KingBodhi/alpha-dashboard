#!/usr/bin/env python3
"""
Bitcoin Core RPC Configuration Helper
This tool helps set up Bitcoin Core RPC for the dashboard.
"""

import subprocess
import os
import sys
from pathlib import Path

def find_bitcoin_config():
    """Find Bitcoin Core configuration file."""
    print("🔍 Looking for Bitcoin Core configuration...")
    
    # Common Bitcoin Core data directory locations
    possible_dirs = [
        Path.home() / ".bitcoin",  # Default on Linux/macOS
        Path.home() / "Library" / "Application Support" / "Bitcoin",  # macOS app
        Path.home() / "AppData" / "Roaming" / "Bitcoin",  # Windows
    ]
    
    for data_dir in possible_dirs:
        if data_dir.exists():
            config_file = data_dir / "bitcoin.conf"
            print(f"📁 Found Bitcoin data directory: {data_dir}")
            
            if config_file.exists():
                print(f"✅ Found bitcoin.conf: {config_file}")
                return data_dir, config_file
            else:
                print(f"❌ No bitcoin.conf found in {data_dir}")
                return data_dir, config_file  # Return path even if file doesn't exist
    
    print(f"❌ No Bitcoin data directory found")
    return None, None

def check_bitcoin_process():
    """Check if Bitcoin Core is running."""
    print(f"\n🔍 Checking if Bitcoin Core is running...")
    
    try:
        # Check for Bitcoin Core process
        result = subprocess.run(['pgrep', '-f', 'bitcoind'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Bitcoin Core is running (PID: {result.stdout.strip()})")
            return True
        else:
            print(f"❌ Bitcoin Core is not running")
            return False
            
    except Exception as e:
        print(f"❌ Could not check Bitcoin process: {e}")
        return False

def create_bitcoin_config(data_dir, config_file):
    """Create or update bitcoin.conf for RPC access."""
    print(f"\n🔧 Setting up bitcoin.conf for RPC access...")
    
    # Generate random RPC credentials
    import secrets
    import string
    
    rpc_user = "dashboard_user"
    rpc_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    
    config_content = f"""# Bitcoin Core Configuration for Alpha Dashboard
# RPC Configuration
server=1
rpcuser={rpc_user}
rpcpassword={rpc_password}
rpcallowip=127.0.0.1
rpcport=8332

# Enable wallet functionality
wallet=

# Optional: Reduce log verbosity
debug=0

# Performance settings (optional)
dbcache=512
maxmempool=300
"""
    
    try:
        # Create data directory if it doesn't exist
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        print(f"✅ Created bitcoin.conf at: {config_file}")
        print(f"📝 RPC Credentials:")
        print(f"   User: {rpc_user}")
        print(f"   Password: {rpc_password}")
        
        return rpc_user, rpc_password
        
    except Exception as e:
        print(f"❌ Failed to create bitcoin.conf: {e}")
        return None, None

def update_dashboard_config(rpc_user, rpc_password):
    """Update dashboard configuration with new RPC credentials."""
    print(f"\n🔧 Updating dashboard configuration...")
    
    config_file = Path(__file__).parent / "app" / "config" / "bitcoin_config.py"
    
    try:
        # Read current config
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Update RPC credentials
        content = content.replace('"rpc_user": "admin"', f'"rpc_user": "{rpc_user}"')
        content = content.replace('"rpc_password": "admin123"', f'"rpc_password": "{rpc_password}"')
        
        # Write updated config
        with open(config_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated dashboard configuration")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update dashboard config: {e}")
        return False

def test_rpc_connection(rpc_user, rpc_password):
    """Test RPC connection to Bitcoin Core."""
    print(f"\n🧪 Testing RPC connection...")
    
    try:
        from bitcoinrpc.authproxy import AuthServiceProxy
        
        rpc_url = f"http://{rpc_user}:{rpc_password}@127.0.0.1:8332"
        rpc = AuthServiceProxy(rpc_url, timeout=10)
        
        # Test connection
        info = rpc.getblockchaininfo()
        
        print(f"✅ RPC connection successful!")
        print(f"📊 Blockchain info:")
        print(f"   Chain: {info.get('chain', 'unknown')}")
        print(f"   Blocks: {info.get('blocks', 0):,}")
        print(f"   Sync: {info.get('verificationprogress', 0) * 100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ RPC connection failed: {e}")
        return False

def main():
    """Main configuration setup."""
    print("🔧 Bitcoin Core RPC Configuration for Alpha Dashboard")
    print("=" * 60)
    
    # Step 1: Check if Bitcoin Core is running
    if not check_bitcoin_process():
        print(f"\n❌ Bitcoin Core is not running!")
        print(f"💡 Please start Bitcoin Core first, then run this script again.")
        print(f"   On macOS: Open Bitcoin Core app")
        print(f"   On Linux: bitcoind -daemon")
        return
    
    # Step 2: Find Bitcoin configuration
    data_dir, config_file = find_bitcoin_config()
    
    if not data_dir:
        print(f"\n❌ Could not find Bitcoin data directory!")
        print(f"💡 Please make sure Bitcoin Core is installed and has been run at least once.")
        return
    
    # Step 3: Check if bitcoin.conf exists and has RPC enabled
    rpc_user, rpc_password = None, None
    
    if config_file.exists():
        print(f"\n📝 Reading existing bitcoin.conf...")
        with open(config_file, 'r') as f:
            content = f.read()
        
        if 'rpcuser=' in content and 'rpcpassword=' in content:
            print(f"✅ RPC is already configured in bitcoin.conf")
            
            # Extract credentials
            for line in content.split('\n'):
                if line.startswith('rpcuser='):
                    rpc_user = line.split('=', 1)[1].strip()
                elif line.startswith('rpcpassword='):
                    rpc_password = line.split('=', 1)[1].strip()
            
            print(f"📝 Existing RPC credentials found")
        else:
            print(f"⚠️ bitcoin.conf exists but RPC not configured")
            response = input("Add RPC configuration to existing file? (y/n): ")
            if response.lower().startswith('y'):
                # Backup existing config
                backup_file = config_file.with_suffix('.conf.backup')
                config_file.rename(backup_file)
                print(f"📋 Backed up existing config to: {backup_file}")
                
                rpc_user, rpc_password = create_bitcoin_config(data_dir, config_file)
    else:
        print(f"\n📝 No bitcoin.conf found, creating new one...")
        rpc_user, rpc_password = create_bitcoin_config(data_dir, config_file)
    
    if not rpc_user or not rpc_password:
        print(f"\n❌ Failed to set up RPC credentials")
        return
    
    # Step 4: Update dashboard configuration
    if update_dashboard_config(rpc_user, rpc_password):
        print(f"\n✅ Dashboard configuration updated!")
    
    # Step 5: Test connection
    print(f"\n⚠️ Bitcoin Core needs to be restarted to use new RPC settings")
    print(f"💡 Please restart Bitcoin Core, then test the connection")
    
    input("\nPress Enter after restarting Bitcoin Core to test connection...")
    
    if test_rpc_connection(rpc_user, rpc_password):
        print(f"\n🎉 SUCCESS! Bitcoin Core RPC is now configured for the dashboard")
        print(f"\n🚀 You can now run the dashboard:")
        print(f"   python main.py")
    else:
        print(f"\n❌ Connection still failed after restart")
        print(f"💡 Check that Bitcoin Core restarted successfully")
        print(f"💡 Check for any errors in Bitcoin Core debug.log")

if __name__ == "__main__":
    main()
