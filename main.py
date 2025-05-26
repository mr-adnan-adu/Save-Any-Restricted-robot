import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait
import os
import logging
import re

# Basic configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")
OWNER_ID = int(os.environ.get("OWNER_ID"))

# Initialize clients
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Rate limiting storage
user_cooldown = {}

async def handle_link(client: Client, message: Message):
    user_id = message.from_user.id
    
    # Basic rate limiting
    if user_id in user_cooldown:
        await message.reply("⚠️ Please wait 5 seconds between requests")
        return
    
    user_cooldown[user_id] = True
    
    try:
        link = message.text
        if "t.me/c/" in link or "t.me/+" in link:
            # Parse message IDs from link
            parts = re.findall(r't\.me/(?:c/|)(\d+)/(\d+)', link)
            if not parts:
                await message.reply("❌ Invalid link format")
                return

            chat_id, msg_id = parts[0]
            msg = await userbot.get_messages(int(chat_id), int(msg_id))
            
            if msg:
                await msg.copy(message.chat.id)
                logger.info(f"Sent message {msg_id} from {chat_id}")
            else:
                await message.reply("❌ Message not found")
            
            # Reset cooldown after 5 seconds
            await asyncio.sleep(5)
            del user_cooldown[user_id]
            
    except FloodWait as e:
        await message.reply(f"⏳ Please wait {e.value} seconds")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await message.reply("❌ Error processing request")

@bot.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    await message.reply(
        "🤖 **Simple Content Bot**\n\n"
        "Send me any Telegram message link and I'll forward it to you!\n\n"
        "Example links:\n"
        "- `t.me/c/123456789/1`\n"
        "- `t.me/channelname/123`"
    )

@bot.on_message(filters.text & filters.private)
async def message_handler(client: Client, message: Message):
    if any(link in message.text for link in ["t.me/c/", "t.me/+"]):
        await handle_link(client, message)

async def main():
    await bot.start()
    await userbot.start()
    logger.info("Bot started!")
    await idle()  # This keeps the bot running
    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.run(main())
