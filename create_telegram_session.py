#!/usr/bin/env python3
"""
Simple script to create Telegram session file for FFI Crypto Bot
This only needs to be run once to authenticate with Telegram.
"""

import os
import sys

try:
    from telethon.sync import TelegramClient
except ImportError:
    print("❌ Telethon not installed. Installing now...")
    os.system("pip3 install telethon")
    from telethon.sync import TelegramClient

def main():
    print("=" * 60)
    print("FFI Crypto Bot - Telegram Session Creator")
    print("=" * 60)
    print()
    
    # Get credentials
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone = os.getenv('TELEGRAM_PHONE')
    
    # Check if credentials are provided
    if not api_id:
        api_id = input("Enter your Telegram API ID: ").strip()
    
    if not api_hash:
        api_hash = input("Enter your Telegram API Hash: ").strip()
    
    if not phone:
        phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
    
    if not all([api_id, api_hash, phone]):
        print("❌ Error: All credentials are required!")
        sys.exit(1)
    
    print()
    print("📱 Connecting to Telegram...")
    print("You will receive a verification code via Telegram.")
    print()
    
    # Create the client
    client = TelegramClient('ffi_crypto_bot', api_id, api_hash)
    
    try:
        # Start the client (this will prompt for code)
        client.start(phone=phone)
        
        print()
        print("✅ Authentication successful!")
        print()
        print("📁 Session file created: ffi_crypto_bot.session")
        print()
        print("Next steps:")
        print("1. Upload 'ffi_crypto_bot.session' to your GitHub repository")
        print("2. Or encode it as base64 and add as GitHub Secret:")
        print("   base64 ffi_crypto_bot.session")
        print()
        print("See TELEGRAM_AUTHENTICATION_GUIDE.md for detailed instructions.")
        
        # Test the connection by getting dialogs
        print()
        print("🔍 Testing connection by fetching your Telegram dialogs...")
        dialogs = client.get_dialogs(limit=5)
        print(f"✅ Successfully connected! Found {len(dialogs)} recent chats.")
        
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

