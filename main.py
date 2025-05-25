from pyrogram import Client, filters, idle
from pyrogram.types import Message
import asyncio
import os
import logging
from datetime import datetime, timedelta

# Enable logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables with validation
try:
    API_ID = int(os.environ.get("API_ID"))
    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    SESSION_STRING = os.environ.get("USERBOT_SESSION_STRING")
    
    logger.info(f"API_ID: {API_ID}")
    logger.info(f"API_HASH: {'*' * len(API_HASH) if API_HASH else 'NOT SET'}")
    logger.info(f"BOT_TOKEN: {'*' * 20 if BOT_TOKEN else 'NOT SET'}")
    logger.info(f"SESSION_STRING: {'*' * 20 if SESSION_STRING else 'NOT SET'}")
    
    if not all([API_ID, API_HASH, BOT_TOKEN, SESSION_STRING]):
        raise ValueError("Missing required environment variables")
        
except Exception as e:
    logger.error(f"Environment setup error: {e}")
    raise

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
        logger.info(f"Fetching message {msg_id} from chat {chat_id}")
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not msg:
            await message.reply(f"⚠️ Message {msg_id} not found or deleted.")
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
            await message.reply("⚠️ Unsupported message type.")
            
        logger.info(f"Successfully sent message {msg_id}")
        await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Error fetching message {msg_id}: {e}")
        await message.reply(f"❌ Error fetching message ID {msg_id}: {e}")

@bot.on_message(filters.private)
async def handle_all_messages(_, message: Message):
    logger.info(f"Received message from {message.from_user.id}: {message.text[:50] if message.text else 'Non-text message'}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/c/\d+/\d+(-\d+)?'))
async def handle_private_link(_, message: Message):
    logger.info(f"Processing private link from user {message.from_user.id}")
    
    if is_rate_limited(message.from_user.id):
        await message.reply("⏳ Please wait a few seconds before making another request.")
        return
        
    try:
        link = message.text.strip()
        parts = link.split("/")
        chat_id = int("-100" + parts[4])
        msg_id_part = parts[5]

        logger.info(f"Parsed chat_id: {chat_id}, msg_id_part: {msg_id_part}")

        # Check access
        try:
            chat_info = await userbot.get_chat(chat_id)
            logger.info(f"Successfully accessed chat: {chat_info.title}")
        except Exception as e:
            logger.error(f"Cannot access chat {chat_id}: {e}")
            await message.reply(f"❌ Cannot access chat (maybe not joined): {e}")
            return

        if "-" in msg_id_part:
            start_id, end_id = map(int, msg_id_part.split("-"))
            
            if end_id - start_id > 50:
                await message.reply("⚠️ Range too large. Maximum 50 messages at once.")
                return
                
            await message.reply(f"📥 Fetching messages {start_id} to {end_id}...")
            
            for msg_id in range(start_id, end_id + 1):
                await fetch_and_send(chat_id, msg_id, message)
        else:
            await fetch_and_send(chat_id, int(msg_id_part), message)
            
    except Exception as e:
        logger.error(f"Error parsing link: {e}")
        await message.reply(f"⚠️ Error parsing link: {e}")

@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def handle_invite(_, message: Message):
    logger.info(f"Processing invite link from user {message.from_user.id}")
    
    if is_rate_limited(message.from_user.id):
        await message.reply("⏳ Please wait before joining another chat.")
        return
        
    invite_link = message.text.strip()
    logger.info(f"Invite link: {invite_link}")
    
    try:
        if not userbot.is_connected:
            await userbot.start()
            logger.info("Userbot started for chat joining")

        chat = await userbot.join_chat(invite_link)
        logger.info(f"Successfully joined chat: {chat.title} (ID: {chat.id})")
        await message.reply(f"✅ Successfully joined: {chat.title}")
        
    except Exception as e:
        logger.error(f"Failed to join chat: {e}")
        await message.reply(f"❌ Failed to join: {e}")

@bot.on_message(filters.private & filters.command("start"))
async def start_command(_, message: Message):
    logger.info(f"Start command from user {message.from_user.id}")
    welcome_text = f"""
🤖 **Bot is Working!**

Hello {message.from_user.first_name}! 

**Bot Status:** ✅ Online
**User ID:** `{message.from_user.id}`
**Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`

**Usage:**
• Send private channel link: `https://t.me/c/123456789/1`
• Send invite link: `https://t.me/+abcd1234`
• Send `/test` to test bot functionality
    """
    await message.reply(welcome_text)

@bot.on_message(filters.private & filters.command("test"))
async def test_command(_, message: Message):
    logger.info(f"Test command from user {message.from_user.id}")
    
    try:
        # Test userbot connection
        userbot_me = await userbot.get_me()
        bot_me = await bot.get_me()
        
        test_result = f"""
🧪 **Bot Test Results**

**Bot Status:** ✅ Working
**Bot Username:** @{bot_me.username}
**Userbot Status:** ✅ Connected
**Userbot Name:** {userbot_me.first_name}

**Functionality:**
✅ Bot can receive messages
✅ Userbot is connected
✅ Rate limiting is active
✅ All systems operational

**Next Steps:**
1. Join a private channel with userbot account
2. Send channel link to test message fetching
        """
        await message.reply(test_result)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        await message.reply(f"❌ Test failed: {e}")

async def main():
    try:
        logger.info("Starting bot initialization...")
        
        await bot.start()
        logger.info("Bot client started successfully")
        
        await userbot.start()
        logger.info("Userbot client started successfully")
        
        # Get bot info
        me = await bot.get_me()
        userbot_me = await userbot.get_me()
        
        logger.info(f"Bot started successfully!")
        logger.info(f"Bot username: @{me.username}")
        logger.info(f"Bot ID: {me.id}")
        logger.info(f"Userbot name: {userbot_me.first_name}")
        logger.info(f"Userbot ID: {userbot_me.id}")
        
        print(f"🤖 Bot @{me.username} is now running!")
        print(f"👤 Userbot: {userbot_me.first_name}")
        print("Bot is ready to receive messages...")
        
        await idle()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Bot startup failed: {e}")
        raise
    finally:
        logger.info("Shutting down...")
        await bot.stop()
        await userbot.stop()
        logger.info("Bot and Userbot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
