from pyrogram import Client

api_id = int(input("Enter your API_ID: 8078347 "))
api_hash = input("Enter your API_HASH: 721e258069f64e1ecb75c56907927ff2")

with Client("userbot", api_id, api_hash) as app:
    print("Session string:", app.export_session_string())
