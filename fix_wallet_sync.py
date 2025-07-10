#!/usr/bin/env python3
"""
Wallet-Dashboard Sync Fixer
This tool helps sync your Bitcoin Core wallet with the dashboard.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def fix_wallet_dashboard_sync():
    """Help sync Bitcoin Core wallet with dashboard."""
    print("🔧 Wallet-Dashboard Sync Fixer")
    print("=" * 50)
    
    # Get dashboard address
    dashboard_address = "bc1qyd9gdhsk9952dylkrw9c3tktve38d4lewj6t5s"  # From diagnostic
    print(f"Dashboard is monitoring: {dashboard_address}")
    
    print(f"\n📋 Step-by-Step Fix Instructions:")
    print(f"=" * 40)
    
    print(f"\n🔍 STEP 1: Check if dashboard address has funds in Bitcoin Core")
    print(f"Run this in Bitcoin Core console or bitcoin-cli:")
    print(f"")
    print(f"   scantxoutset \"start\" '[\"addr({dashboard_address})\"]'")
    print(f"")
    print(f"This will show if the address has any UTXOs.")
    print(f"If it shows balance > 0, the dashboard should detect it.")
    print(f"If it shows 0, the address is empty.")
    
    print(f"\n🔍 STEP 2: Check which addresses in your wallet have funds")
    print(f"Run this in Bitcoin Core console:")
    print(f"")
    print(f"   listunspent")
    print(f"")
    print(f"This shows all UTXOs in your wallet with their addresses.")
    print(f"Look for addresses with funds that you want to monitor.")
    
    print(f"\n🔧 STEP 3A: If dashboard address is empty but wallet has funds")
    print(f"Option 1 - Import funded address to dashboard:")
    print(f"1. Find an address with funds from listunspent")
    print(f"2. Export its private key: dumpprivkey <address>")
    print(f"3. Replace dashboard profile with this private key")
    print(f"")
    print(f"Option 2 - Import dashboard address to wallet:")
    print(f"1. Get dashboard private key from profile")
    print(f"2. Import to Bitcoin Core: importprivkey <private_key>")
    print(f"3. Send funds to dashboard address")
    
    print(f"\n🔧 STEP 3B: If dashboard address has funds but dashboard shows 0")
    print(f"This indicates a technical issue with balance detection.")
    print(f"Check:")
    print(f"1. Bitcoin Core is fully synced")
    print(f"2. Dashboard is connected to Bitcoin Core") 
    print(f"3. No RPC errors in dashboard console")
    
    print(f"\n🧪 STEP 4: Test with manual RPC call")
    print(f"Test the exact same call the dashboard uses:")
    print(f"")
    print(f"   scantxoutset \"start\" '[\"addr({dashboard_address})\"]'")
    print(f"")
    print(f"If this returns funds but dashboard shows 0, there's a bug.")
    print(f"If this returns 0, the address is empty.")
    
    print(f"\n📞 STEP 5: Quick diagnostic commands")
    print(f"Run these to gather information:")
    print(f"")
    print(f"# Check wallet balance")
    print(f"getwalletinfo")
    print(f"")
    print(f"# Check specific address")
    print(f"getaddressinfo {dashboard_address}")
    print(f"")
    print(f"# Check if address is in wallet")
    print(f"getaddressesbylabel \"\"")
    
    # Interactive helper
    print(f"\n🤖 Interactive Helper")
    print(f"=" * 25)
    
    try:
        print(f"\nLet's identify your specific issue:")
        print(f"")
        
        response1 = input("Does 'getwalletinfo' show balance > 0? (y/n): ").lower().strip()
        
        if response1.startswith('y'):
            print(f"✅ Your wallet has funds")
            
            response2 = input(f"Does 'scantxoutset' for {dashboard_address[:20]}... show balance > 0? (y/n): ").lower().strip()
            
            if response2.startswith('y'):
                print(f"✅ Dashboard address has funds")
                print(f"🎯 ISSUE: Dashboard balance detection bug")
                print(f"   - Check dashboard console for errors")
                print(f"   - Restart dashboard")
                print(f"   - Check Bitcoin Core RPC connection")
                
            else:
                print(f"❌ Dashboard address is empty")
                print(f"🎯 ISSUE: Address mismatch")
                print(f"   Solution: Import a funded address to dashboard")
                print(f"   1. Run 'listunspent' to find funded addresses")
                print(f"   2. Run 'dumpprivkey <address>' for a funded address")
                print(f"   3. Update dashboard profile with that private key")
                
        else:
            print(f"❌ Your wallet shows no funds")
            print(f"🎯 ISSUE: No funds in Bitcoin Core wallet")
            print(f"   - Check if you're connected to the right wallet")
            print(f"   - Check if Bitcoin Core is fully synced")
            print(f"   - Verify you're on the right network (mainnet/testnet)")
            
    except KeyboardInterrupt:
        print(f"\nSkipping interactive helper...")
    
    print(f"\n🎯 Most Likely Solution:")
    print(f"Based on common issues, try this:")
    print(f"1. Run: listunspent")
    print(f"2. Find an address with funds")
    print(f"3. Run: dumpprivkey <that_address>")
    print(f"4. Update dashboard profile with that private key")
    print(f"5. Restart dashboard")

if __name__ == "__main__":
    fix_wallet_dashboard_sync()
