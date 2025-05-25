import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH)
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def join_private_channel(_, message: Message):
    invite_link = message.text.strip()
    try:
        await userbot.join_chat(invite_link)
        await message.reply("✅ Joined the private channel successfully.")
    except Exception as e:
        await message.reply(f"❌ Failed to join: {e}")


@bot.on_message(filters.private & filters.regex(r'https://t\.me/c/\d+/\d+(-\d+)?'))
async def get_message(_, message: Message):
    link = message.text.strip()
    parts = link.split("/")
    chat_id = int("-100" + parts[4])
    msg_id_part = parts[5]

    if "-" in msg_id_part:
        start_id, end_id = map(int, msg_id_part.split("-"))
        for msg_id in range(start_id, end_id + 1):
            await fetch_and_send(chat_id, msg_id, message)
    else:
        await fetch_and_send(chat_id, int(msg_id_part), message)


async def fetch_and_send(chat_id, msg_id, reply_to):
    try:
        msg = await userbot.get_messages(chat_id, msg_id)
        if msg.media:
            downloaded = await msg.download()
            await bot.send_document(chat_id=reply_to.chat.id, document=downloaded)
        elif msg.text:
            await bot.send_message(reply_to.chat.id, msg.text)
        else:
            await bot.send_message(reply_to.chat.id, "ℹ️ Message has no text or media.")
    except Exception as e:
        await bot.send_message(reply_to.chat.id, f"❌ Error: {e}")


async def main():
    await userbot.start()
    await bot.start()
    print("✅ Bot and Userbot started.")
    await asyncio.get_event_loop().create_future()

asyncio.run(main())
