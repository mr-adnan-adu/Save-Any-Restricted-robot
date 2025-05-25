from pyrogram import Client, filters, idle
from pyrogram.types import Message
import asyncio
import os

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("USERBOT_SESSION_STRING")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

async def fetch_and_send(chat_id, msg_id, message):
    try:
        msg = await userbot.get_messages(chat_id, msg_id)
        if msg.text or msg.caption:
            await message.reply(msg.text or msg.caption)
        elif msg.document:
            await message.reply_document(msg.document.file_id, caption=msg.caption or "")
        elif msg.photo:
            await message.reply_photo(msg.photo.file_id, caption=msg.caption or "")
        else:
            await message.reply("⚠️ Unsupported message type.")
    except Exception as e:
        await message.reply(f"❌ Error fetching message ID {msg_id}: {e}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/c/\d+/\d+(-\d+)?'))
async def handle_private_link(_, message: Message):
    try:
        link = message.text.strip()
        parts = link.split("/")
        chat_id = int("-100" + parts[4])
        msg_id_part = parts[5]

        # Check access
        try:
            await userbot.get_chat(chat_id)
        except Exception as e:
            await message.reply(f"❌ Cannot access chat (maybe not joined): {e}")
            return

        if "-" in msg_id_part:
            start_id, end_id = map(int, msg_id_part.split("-"))
            for msg_id in range(start_id, end_id + 1):
                await fetch_and_send(chat_id, msg_id, message)
        else:
            await fetch_and_send(chat_id, int(msg_id_part), message)
    except Exception as e:
        await message.reply(f"⚠️ Error parsing link: {e}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def handle_invite(_, message: Message):
    invite_link = message.text.strip()
    print(f"[DEBUG] Invite link received: {invite_link}")
    try:
        if not userbot.is_connected:
            await userbot.start()
            print("[DEBUG] Userbot started to join chat.")

        chat = await userbot.join_chat(invite_link)
        print(f"[DEBUG] Joined chat: {chat.title} (ID: {chat.id})")
        await message.reply(f"✅ Successfully joined: {chat.title}")
    except Exception as e:
        print(f"[ERROR] Failed to join chat: {e}")
        await message.reply(f"❌ Failed to join: {e}")

async def main():
    await bot.start()
    await userbot.start()
    print("[INFO] Bot and Userbot started.")
    await idle()
    await bot.stop()
    await userbot.stop()
    print("[INFO] Bot and Userbot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
