#!/usr/bin/env python3
"""
Debug script to check what might be breaking the Bitcoin Core connection.
"""

def check_integration_methods():
    """Check if all required methods exist in the pages."""
    print("🧪 Checking Bitcoin Core Integration Methods")
    print("=" * 60)
    
    # Check if methods exist
    try:
        from app.pages.profile_page import ProfilePage
        profile = ProfilePage()
        
        print("✅ ProfilePage methods:")
        methods = ['on_bitcoin_core_connected', 'on_bitcoin_core_disconnected', 'set_bitcoin_service']
        for method in methods:
            if hasattr(profile, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - MISSING!")
        
    except Exception as e:
        print(f"❌ Error importing ProfilePage: {e}")
    
    try:
        from app.pages.transaction_page import TransactionPage
        transaction = TransactionPage()
        
        print("\n✅ TransactionPage methods:")
        methods = ['on_bitcoin_core_connected', 'on_bitcoin_core_disconnected', 'set_bitcoin_service']
        for method in methods:
            if hasattr(transaction, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - MISSING!")
        
    except Exception as e:
        print(f"❌ Error importing TransactionPage: {e}")

def suggest_fixes():
    """Suggest potential fixes."""
    print("\n🔧 Potential Issues and Fixes:")
    print("1. Method call timing - pages not ready when called")
    print("2. Exception in callback methods - breaking connection flow")
    print("3. Import/initialization errors in new methods")
    print("4. Circular import or dependency issues")
    
    print("\n✅ Applied Fixes:")
    print("• Added delayed transaction page update (QTimer.singleShot)")
    print("• Added individual try/catch for each page update")
    print("• Added detailed error logging")
    print("• Added fallback handling for missing wallet addresses")

def main():
    """Run debug checks."""
    print("🚀 Bitcoin Core Connection Debug Check")
    print("=" * 80)
    
    check_integration_methods()
    suggest_fixes()
    
    print("\n🔄 To test the fix:")
    print("1. Start the application")
    print("2. Go to Bitcoin tab and click Connect")
    print("3. Check terminal output for detailed connection flow")
    print("4. Verify Profile and Transaction pages load wallet addresses")

if __name__ == "__main__":
    main()