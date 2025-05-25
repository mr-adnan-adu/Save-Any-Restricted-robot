from pyrogram import Client, filters, idle
from pyrogram.types import Message
import asyncio
import os
from datetime import datetime, timedelta

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("USERBOT_SESSION_STRING")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Rate limiting
user_last_request = {}
RATE_LIMIT_SECONDS = 5

def is_rate_limited(user_id):
    now = datetime.now()
    if user_id in user_last_request:
        if now - user_last_request[user_id] < timedelta(seconds=RATE_LIMIT_SECONDS):
            return True
    user_last_request[user_id] = now
    return False

async def fetch_and_send(chat_id, msg_id, message):
    try:
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not msg:
            await message.reply(f"⚠ Message {msg_id} not found or deleted.")
            return
            
        if msg.text or msg.caption:
            await message.reply(msg.text or msg.caption)
        elif msg.document:
            await message.reply_document(msg.document.file_id, caption=msg.caption or "")
        elif msg.photo:
            await message.reply_photo(msg.photo.file_id, caption=msg.caption or "")
        elif msg.video:
            await message.reply_video(msg.video.file_id, caption=msg.caption or "")
        elif msg.audio:
            await message.reply_audio(msg.audio.file_id, caption=msg.caption or "")
        elif msg.voice:
            await message.reply_voice(msg.voice.file_id, caption=msg.caption or "")
        elif msg.sticker:
            await message.reply_sticker(msg.sticker.file_id)
        else:
            await message.reply("⚠ Unsupported message type.")
            
        # Add small delay to prevent flood
        await asyncio.sleep(1)
        
    except Exception as e:
        await message.reply(f"❌ Error fetching message ID {msg_id}: {e}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/c/\d+/\d+(-\d+)?'))
async def handle_private_link(_, message: Message):
    # Rate limiting check
    if is_rate_limited(message.from_user.id):
        await message.reply("⏳ Please wait a few seconds before making another request.")
        return
        
    try:
        link = message.text.strip()
        parts = link.split("/")
        chat_id = int("-100" + parts[4])
        msg_id_part = parts[5]

        # Check access
        try:
            chat_info = await userbot.get_chat(chat_id)
            print(f"[DEBUG] Accessing chat: {chat_info.title}")
        except Exception as e:
            await message.reply(f"❌ Cannot access chat (maybe not joined): {e}")
            return

        if "-" in msg_id_part:
            start_id, end_id = map(int, msg_id_part.split("-"))
            
            # Limit range to prevent abuse
            if end_id - start_id > 50:
                await message.reply("⚠ Range too large. Maximum 50 messages at once.")
                return
                
            await message.reply(f"📥 Fetching messages {start_id} to {end_id}...")
            
            for msg_id in range(start_id, end_id + 1):
                await fetch_and_send(chat_id, msg_id, message)
        else:
            await fetch_and_send(chat_id, int(msg_id_part), message)
            
    except Exception as e:
        await message.reply(f"⚠ Error parsing link: {e}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def handle_invite(_, message: Message):
    # Rate limiting check
    if is_rate_limited(message.from_user.id):
        await message.reply("⏳ Please wait before joining another chat.")
        return
        
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

@bot.on_message(filters.private & filters.command("start"))
async def start_command(_, message: Message):
    welcome_text = """
🤖 *Restricted Content Saver Bot*

*Features:*
• Save messages from private/restricted channels
• Join channels via invite links
• Download media files

*Usage:*
1. Send a private channel link: https://t.me/c/123456789/1
2. Send invite link to join: https://t.me/+abcd1234
3. For message ranges: https://t.me/c/123456789/1-10

*Note:* Bot needs to be in the channel to access messages.
    """
    await message.reply(welcome_text)

@bot.on_message(filters.private & filters.command("help"))
async def help_command(_, message: Message):
    help_text = """
📚 *Help & Commands*

*Supported Links:*
• https://t.me/c/1234567890/123 - Single message
• https://t.me/c/1234567890/123-130 - Message range (max 50)
• https://t.me/+abcd1234 - Invite link to join

*Supported Media:*
• Text messages
• Photos & Videos
• Documents & Files
• Audio & Voice messages
• Stickers

*Rate Limits:*
• 1 request per 5 seconds per user
• Maximum 50 messages per range request
    """
    await message.reply(help_text)

async def main():
    try:
        await bot.start()
        await userbot.start()
        print("[INFO] Bot and Userbot started successfully.")
        
        # Get bot info
        me = await bot.get_me()
        print(f"[INFO] Bot username: @{me.username}")
        
        await idle()
        
    except Exception as e:
        print(f"[ERROR] Failed to start: {e}")
    finally:
        await bot.stop()
        await userbot.stop()
        print("[INFO] Bot and Userbot stopped.")

if _name_ == "_main_":
    asyncio.run(main())
