from pyrogram import Client
import os

API_ID = int(input("Enter your API_ID: 1980071557 "))
API_HASH = input("Enter your API_HASH: 721e258069f64e1ecb75c56907927ff2 ")
PHONE = input("Enter your phone number (with country code): +919562493851 ")

app = Client("userbot", api_id=API_ID, api_hash=API_HASH)

app.connect()
if not app.is_authorized():
    try:
        app.send_code_request(PHONE)
        code = input("Enter the code you received: ")
        app.sign_in(PHONE, code)
        print("✅ Session created successfully!")
    except Exception as e:
        print(f"❌ Failed to create session: {e}")
else:
    print("✅ Already authorized!")

app.disconnect()
