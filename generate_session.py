from pyrogram import Client

api_id = int(input("Enter your API_ID: "))
api_hash = input("Enter your API_HASH: ")

with Client("userbot", api_id, api_hash) as app:
    print("Session string:", app.export_session_string())
