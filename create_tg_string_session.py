import os
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = os.getenv("38880809", "").strip()
API_HASH = os.getenv("9659d4cfc3b7c3476089fb218f57e0fc", "").strip()

if not API_ID or not API_HASH:
    raise RuntimeError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH first.")

print("Creating a new Telegram StringSession...")
print("You will be asked for your phone number, Telegram code, and 2FA password if enabled.\n")

with TelegramClient(StringSession(), int(API_ID), API_HASH) as client:
    session_string = client.session.save()
    print("\n" + "=" * 80)
    print("SUCCESS - COPY THE VALUE BELOW")
    print("Railway variable name: TELEGRAM_SESSION_STRING")
    print("=" * 80)
    print(session_string)
    print("=" * 80)
    print("\nDo NOT publish this value or commit it to GitHub.")
