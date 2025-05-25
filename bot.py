import os
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

bot = Client("save_restricted_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

channel_invites = {}  # In-memory cache for invite links

HELP_TEXT = """
**Help:**

1. Send me any post link like `https://t.me/c/...`
2. If it's from a **private channel**, first send the **invite link**
3. I will automatically download and send the content.

• I support Files 📁 and Messages!
"""

@bot.on_message(filters.command(["start", "help"]))
async def help_handler(client, message: Message):
    await message.reply_text(HELP_TEXT)

@bot.on_message(filters.private & filters.text)
async def handle_text(client, message: Message):
    text = message.text.strip()

    if "t.me/joinchat/" in text or "t.me/+" in text:
        try:
            chat = await client.join_chat(text)
            channel_invites[str(chat.id)] = text
            await message.reply_text(f"✅ Joined: **{chat.title}**.\nNow send the post link.")
        except Exception as e:
            return await message.reply_text(f"❌ Failed to join: {e}")
        return

    if text.startswith("https://t.me/c/"):
        try:
            parts = text.split("/")
            chat_id = int("-100" + parts[4])
            msg_id = int(parts[5])

            try:
                msg = await client.get_messages(chat_id, msg_id)
            except:
                invite = channel_invites.get(str(chat_id))
                if invite:
                    await client.join_chat(invite)
                    msg = await client.get_messages(chat_id, msg_id)
                else:
                    return await message.reply_text("🔒 Private channel detected.\nPlease send the invite link first.")

            if msg.media:
                await message.reply_text("📥 Downloading content...")
                await msg.copy(message.chat.id)
            else:
                await message.reply_text(msg.text or "📄 This post has no media.")
        except Exception as e:
            await message.reply_text(f"⚠️ Error: {e}")
        return

    await message.reply_text("❓ Please send a valid post or invite link.")

bot.run()
