from pyrogram import Client

API_ID = int(input("API ID: "))
API_HASH = input("API HASH: ")
PHONE = input("Phone number (with country code): ")

app = Client("userbot", api_id=API_ID, api_hash=API_HASH)

app.connect()
if not app.is_authorized():
    app.send_code_request(PHONE)
    code = input("Enter the code you received: ")
    app.sign_in(PHONE, code)
app.disconnect()

print("✅ userbot.session file created.")
