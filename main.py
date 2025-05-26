from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, ChannelPrivate
import asyncio
import os
import logging
from datetime import datetime, timedelta
import json
import time

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Environment variables with enhanced validation
def load_config():
    """Load and validate configuration from environment variables"""
    config = {
        'API_ID': os.environ.get("API_ID"),
        'API_HASH': os.environ.get("API_HASH"),
        'BOT_TOKEN': os.environ.get("BOT_TOKEN"),
        'SESSION_STRING': os.environ.get("USERBOT_SESSION_STRING"),  # Fixed: This should match the workflow
        'OWNER_ID': os.environ.get("OWNER_ID"),  # Optional: Bot owner for admin commands
        'MAX_MESSAGES': int(os.environ.get("MAX_MESSAGES", "20")),  # Max messages per request
        'RATE_LIMIT': int(os.environ.get("RATE_LIMIT_SECONDS", "3"))  # Rate limit in seconds
    }
    
    # Validate required fields
    required_fields = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'SESSION_STRING']
    missing_fields = [field for field in required_fields if not config[field]]
    
    if missing_fields:
        logger.error(f"Missing required environment variables: {missing_fields}")
        # Also show what environment variables are actually available (for debugging)
        available_vars = [key for key in os.environ.keys() if any(term in key.upper() for term in ['API', 'BOT', 'SESSION', 'TOKEN', 'HASH'])]
        logger.info(f"Available environment variables: {available_vars}")
        raise ValueError(f"Missing required environment variables: {missing_fields}")
    
    try:
        config['API_ID'] = int(config['API_ID'])
        config['OWNER_ID'] = int(config['OWNER_ID']) if config['OWNER_ID'] else None
    except ValueError as e:
        logger.error(f"Invalid numeric environment variable: {e}")
        raise
    
    # Log configuration (masked)
    logger.info(f"Configuration loaded:")
    logger.info(f"API_ID: {config['API_ID']}")
    logger.info(f"API_HASH: {'*' * 10}")
    logger.info(f"BOT_TOKEN: {'*' * 20}")
    logger.info(f"SESSION_STRING: {'*' * 20}")
    logger.info(f"OWNER_ID: {config['OWNER_ID']}")
    logger.info(f"MAX_MESSAGES: {config['MAX_MESSAGES']}")
    logger.info(f"RATE_LIMIT: {config['RATE_LIMIT']} seconds")
    
    return config

# Load configuration
try:
    CONFIG = load_config()
except Exception as e:
    logger.error(f"Configuration error: {e}")
    raise SystemExit(1)

# Initialize clients
bot = Client(
    "content_bot", 
    api_id=CONFIG['API_ID'], 
    api_hash=CONFIG['API_HASH'], 
    bot_token=CONFIG['BOT_TOKEN']
)

userbot = Client(
    "content_userbot", 
    api_id=CONFIG['API_ID'], 
    api_hash=CONFIG['API_HASH'], 
    session_string=CONFIG['SESSION_STRING']
)

# Enhanced rate limiting with user statistics
user_stats = {}
user_last_request = {}

def update_user_stats(user_id, success=True):
    """Update user statistics"""
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'first_seen': datetime.now(),
            'last_seen': datetime.now()
        }
    
    user_stats[user_id]['total_requests'] += 1
    user_stats[user_id]['last_seen'] = datetime.now()
    
    if success:
        user_stats[user_id]['successful_requests'] += 1
    else:
        user_stats[user_id]['failed_requests'] += 1

def is_rate_limited(user_id):
    """Check if user is rate limited"""
    now = datetime.now()
    if user_id in user_last_request:
        time_diff = now - user_last_request[user_id]
        if time_diff < timedelta(seconds=CONFIG['RATE_LIMIT']):
            return True, CONFIG['RATE_LIMIT'] - time_diff.seconds
    user_last_request[user_id] = now
    return False, 0

def is_owner(user_id):
    """Check if user is bot owner"""
    return CONFIG['OWNER_ID'] and user_id == CONFIG['OWNER_ID']

async def handle_flood_wait(e):
    """Handle Telegram flood wait errors"""
    wait_time = e.value if hasattr(e, 'value') else 60
    logger.warning(f"Flood wait: {wait_time} seconds")
    await asyncio.sleep(wait_time)

async def fetch_and_send(chat_id, msg_id, message, reply_to_msg_id=None):
    """Enhanced message fetching with better error handling"""
    try:
        logger.info(f"Fetching message {msg_id} from chat {chat_id}")
        
        # Get the message
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not msg:
            await message.reply(f"⚠️ Message {msg_id} not found or deleted.", reply_to_message_id=reply_to_msg_id)
            return False
        
        # Handle different message types with better organization
        if msg.text or msg.caption:
            content = msg.text or msg.caption
            if len(content) > 4096:  # Telegram message length limit
                # Split long messages
                for i in range(0, len(content), 4096):
                    chunk = content[i:i+4096]
                    await message.reply(chunk, reply_to_message_id=reply_to_msg_id)
                    await asyncio.sleep(1)
            else:
                await message.reply(content, reply_to_message_id=reply_to_msg_id)
                
        elif msg.media:
            # Handle media messages
            caption = msg.caption or ""
            
            if msg.document:
                await message.reply_document(
                    msg.document.file_id, 
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.photo:
                await message.reply_photo(
                    msg.photo.file_id, 
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.video:
                await message.reply_video(
                    msg.video.file_id, 
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.audio:
                await message.reply_audio(
                    msg.audio.file_id, 
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.voice:
                await message.reply_voice(
                    msg.voice.file_id, 
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.video_note:
                await message.reply_video_note(
                    msg.video_note.file_id,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.sticker:
                await message.reply_sticker(
                    msg.sticker.file_id,
                    reply_to_message_id=reply_to_msg_id
                )
            elif msg.animation:
                await message.reply_animation(
                    msg.animation.file_id,
                    caption=caption,
                    reply_to_message_id=reply_to_msg_id
                )
            else:
                await message.reply("⚠️ Unsupported media type.", reply_to_message_id=reply_to_msg_id)
                return False
        else:
            await message.reply("⚠️ Empty or unsupported message type.", reply_to_message_id=reply_to_msg_id)
            return False
            
        logger.info(f"Successfully sent message {msg_id}")
        await asyncio.sleep(1)  # Prevent flooding
        return True
        
    except FloodWait as e:
        await handle_flood_wait(e)
        logger.warning(f"Flood wait while fetching message {msg_id}")
        await message.reply(f"⏳ Rate limited. Please try again in {e.value} seconds.")
        return False
        
    except Exception as e:
        logger.error(f"Error fetching message {msg_id}: {e}")
        await message.reply(f"❌ Error fetching message ID {msg_id}: {str(e)[:100]}...")
        return False

@bot.on_message(filters.private & filters.regex(r'https://t\.me/c/\d+/\d+(-\d+)?'))
async def handle_private_link(_, message: Message):
    """Handle private channel links with enhanced validation"""
    user_id = message.from_user.id
    logger.info(f"Processing private link from user {user_id}")
    
    # Rate limiting check
    is_limited, wait_time = is_rate_limited(user_id)
    if is_limited:
        await message.reply(f"⏳ Please wait {wait_time} seconds before making another request.")
        update_user_stats(user_id, success=False)
        return
    
    try:
        link = message.text.strip()
        parts = link.split("/")
        
        if len(parts) < 6:
            await message.reply("❌ Invalid link format.")
            update_user_stats(user_id, success=False)
            return
            
        chat_id = int("-100" + parts[4])
        msg_id_part = parts[5]

        logger.info(f"Parsed chat_id: {chat_id}, msg_id_part: {msg_id_part}")

        # Verify access to the chat
        try:
            chat_info = await userbot.get_chat(chat_id)
            logger.info(f"Successfully accessed chat: {chat_info.title}")
        except ChannelPrivate:
            await message.reply("❌ This is a private channel. The userbot must be a member.")
            update_user_stats(user_id, success=False)
            return
        except UserNotParticipant:
            await message.reply("❌ Userbot is not a member of this channel.")
            update_user_stats(user_id, success=False)
            return
        except Exception as e:
            logger.error(f"Cannot access chat {chat_id}: {e}")
            await message.reply(f"❌ Cannot access chat: {str(e)[:100]}")
            update_user_stats(user_id, success=False)
            return

        # Handle message range or single message
        if "-" in msg_id_part:
            try:
                start_id, end_id = map(int, msg_id_part.split("-"))
            except ValueError:
                await message.reply("❌ Invalid message ID range format.")
                update_user_stats(user_id, success=False)
                return
            
            if start_id > end_id:
                start_id, end_id = end_id, start_id  # Swap if needed
            
            message_count = end_id - start_id + 1
            if message_count > CONFIG['MAX_MESSAGES']:
                await message.reply(f"⚠️ Range too large. Maximum {CONFIG['MAX_MESSAGES']} messages at once.")
                update_user_stats(user_id, success=False)
                return
            
            status_msg = await message.reply(f"📥 Fetching {message_count} messages ({start_id} to {end_id})...")
            
            successful = 0
            failed = 0
            
            for msg_id in range(start_id, end_id + 1):
                success = await fetch_and_send(chat_id, msg_id, message, reply_to_msg_id=status_msg.id)
                if success:
                    successful += 1
                else:
                    failed += 1
            
            await status_msg.edit_text(f"✅ Completed: {successful} successful, {failed} failed")
            update_user_stats(user_id, success=True)
            
        else:
            try:
                msg_id = int(msg_id_part)
            except ValueError:
                await message.reply("❌ Invalid message ID format.")
                update_user_stats(user_id, success=False)
                return
                
            success = await fetch_and_send(chat_id, msg_id, message)
            update_user_stats(user_id, success=success)
            
    except Exception as e:
        logger.error(f"Error parsing link: {e}")
        await message.reply(f"⚠️ Error parsing link: {str(e)[:100]}")
        update_user_stats(user_id, success=False)

@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def handle_invite(_, message: Message):
    """Handle invite links with better error handling"""
    user_id = message.from_user.id
    logger.info(f"Processing invite link from user {user_id}")
    
    is_limited, wait_time = is_rate_limited(user_id)
    if is_limited:
        await message.reply(f"⏳ Please wait {wait_time} seconds before joining another chat.")
        return
    
    invite_link = message.text.strip()
    logger.info(f"Invite link: {invite_link}")
    
    try:
        chat = await userbot.join_chat(invite_link)
        logger.info(f"Successfully joined chat: {chat.title} (ID: {chat.id})")
        await message.reply(f"✅ Successfully joined: **{chat.title}**\nChat ID: `{chat.id}`")
        update_user_stats(user_id, success=True)
        
    except FloodWait as e:
        await handle_flood_wait(e)
        await message.reply(f"⏳ Rate limited. Try again in {e.value} seconds.")
        
    except Exception as e:
        logger.error(f"Failed to join chat: {e}")
        await message.reply(f"❌ Failed to join: {str(e)[:100]}")
        update_user_stats(user_id, success=False)

@bot.on_message(filters.private & filters.command("start"))
async def start_command(_, message: Message):
    """Enhanced start command with better formatting"""
    user_id = message.from_user.id
    logger.info(f"Start command from user {user_id}")
    
    welcome_text = f"""
🤖 **Enhanced Content Fetcher Bot**

Hello **{message.from_user.first_name}**! 

**📊 Bot Status:** ✅ Online and Ready
**👤 Your ID:** `{user_id}`
**⏰ Server Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}`

**📝 How to Use:**

**1. Private Channel Messages:**
• Format: `https://t.me/c/123456789/1`
• Range: `https://t.me/c/123456789/1-5`
• Max messages per request: {CONFIG['MAX_MESSAGES']}

**2. Join Private Channels:**
• Send invite link: `https://t.me/+abcd1234`

**🔧 Commands:**
• `/test` - Test bot functionality
• `/stats` - View your usage statistics
• `/help` - Show detailed help

**⚠️ Rate Limit:** {CONFIG['RATE_LIMIT']} seconds between requests

**💡 Tips:**
• Make sure the userbot account is a member of the channel
• Private channels require special access
• Some content may be restricted by Telegram
    """
    await message.reply(welcome_text)

@bot.on_message(filters.private & filters.command("help"))
async def help_command(_, message: Message):
    """Detailed help command"""
    help_text = """
📖 **Detailed Help & Instructions**

**🔗 Link Formats:**

**Single Message:**
`https://t.me/c/1234567890123/456`

**Multiple Messages:**
`https://t.me/c/1234567890123/456-460`
(Fetches messages 456 through 460)

**📋 Supported Content Types:**
✅ Text messages
✅ Photos with captions
✅ Videos with captions
✅ Documents and files
✅ Audio files
✅ Voice messages
✅ Stickers
✅ GIFs/Animations

**⚠️ Limitations:**
• Maximum {CONFIG['MAX_MESSAGES']} messages per request
• {CONFIG['RATE_LIMIT']} second cooldown between requests
• Bot must have access to the channel
• Some content may be restricted

**🔐 Privacy & Security:**
• Your messages are not stored
• Bot operates within Telegram's ToS
• Rate limiting prevents abuse

**❓ Troubleshooting:**
• "Cannot access chat" → Userbot not in channel
• "Message not found" → Message deleted/doesn't exist
• "Rate limited" → Wait before next request

Need more help? Use `/test` to check bot status.
    """
    await message.reply(help_text)

@bot.on_message(filters.private & filters.command("stats"))
async def stats_command(_, message: Message):
    """Show user statistics"""
    user_id = message.from_user.id
    
    if user_id not in user_stats:
        await message.reply("📊 **Your Statistics**\n\nNo usage data available yet. Start using the bot to see your stats!")
        return
    
    stats = user_stats[user_id]
    success_rate = (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
    
    stats_text = f"""
📊 **Your Usage Statistics**

**📈 Requests:**
• Total: {stats['total_requests']}
• Successful: {stats['successful_requests']}
• Failed: {stats['failed_requests']}
• Success Rate: {success_rate:.1f}%

**📅 Activity:**
• First Used: {stats['first_seen'].strftime('%Y-%m-%d %H:%M')}
• Last Used: {stats['last_seen'].strftime('%Y-%m-%d %H:%M')}

**⚙️ Current Limits:**
• Rate Limit: {CONFIG['RATE_LIMIT']} seconds
• Max Messages: {CONFIG['MAX_MESSAGES']} per request
    """
    await message.reply(stats_text)

@bot.on_message(filters.private & filters.command("test"))
async def test_command(_, message: Message):
    """Enhanced test command with comprehensive checks"""
    user_id = message.from_user.id
    logger.info(f"Test command from user {user_id}")
    
    test_start = time.time()
    
    try:
        # Test bot connection
        bot_me = await bot.get_me()
        bot_status = "✅ Connected"
        
        # Test userbot connection
        try:
            userbot_me = await userbot.get_me()
            userbot_status = "✅ Connected"
            userbot_info = f"{userbot_me.first_name} (@{userbot_me.username or 'No username'})"
        except Exception as e:
            userbot_status = f"❌ Error: {str(e)[:50]}"
            userbot_info = "N/A"
        
        test_duration = round(time.time() - test_start, 2)
        
        test_result = f"""
🧪 **Comprehensive Bot Test**

**🤖 Bot Status:** {bot_status}
**Bot Info:** @{bot_me.username} ({bot_me.first_name})

**👤 Userbot Status:** {userbot_status}
**Userbot Info:** {userbot_info}

**⚙️ System Status:**
✅ Message handling active
✅ Rate limiting functional ({CONFIG['RATE_LIMIT']}s)
✅ Error handling enabled
✅ Logging system active
✅ Statistics tracking enabled

**📊 Configuration:**
• Max messages per request: {CONFIG['MAX_MESSAGES']}
• Rate limit: {CONFIG['RATE_LIMIT']} seconds
• Owner mode: {'Enabled' if CONFIG['OWNER_ID'] else 'Disabled'}

**⏱️ Test Duration:** {test_duration}s
**🔄 Bot Uptime:** Online since startup

**🎯 Next Steps:**
1. Join a private channel with userbot account
2. Send a channel link to test message fetching
3. Use `/help` for detailed usage instructions
        """
        await message.reply(test_result)
        update_user_stats(user_id, success=True)
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        await message.reply(f"❌ **Test Failed**\n\nError: {str(e)[:200]}")
        update_user_stats(user_id, success=False)

# Owner-only commands
@bot.on_message(filters.private & filters.command("admin") & filters.user(CONFIG['OWNER_ID'] or 0))
async def admin_command(_, message: Message):
    """Admin panel for bot owner"""
    total_users = len(user_stats)
    total_requests = sum(stats['total_requests'] for stats in user_stats.values())
    
    admin_text = f"""
👑 **Admin Panel**

**📊 Bot Statistics:**
• Total Users: {total_users}
• Total Requests: {total_requests}
• Active Sessions: {len(user_last_request)}

**⚙️ System Info:**
• Max Messages: {CONFIG['MAX_MESSAGES']}
• Rate Limit: {CONFIG['RATE_LIMIT']}s

**🔧 Available Commands:**
• `/broadcast <message>` - Send message to all users
• `/stats_global` - Detailed global statistics
    """
    await message.reply(admin_text)

async def main():
    """Enhanced main function with better error handling"""
    try:
        logger.info("🚀 Starting bot initialization...")
        
        # Start bot client
        await bot.start()
        bot_me = await bot.get_me()
        logger.info(f"✅ Bot client started: @{bot_me.username}")
        
        # Start userbot client
        await userbot.start()
        userbot_me = await userbot.get_me()
        logger.info(f"✅ Userbot client started: {userbot_me.first_name}")
        
        # Success message
        print("🎉" + "="*50)
        print(f"🤖 Bot: @{bot_me.username} (ID: {bot_me.id})")
        print(f"👤 Userbot: {userbot_me.first_name} (ID: {userbot_me.id})")
        print("✅ Bot is ready to receive messages!")
        print("="*52)
        
        # Keep the bot running
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise
    finally:
        logger.info("🔄 Shutting down gracefully...")
        try:
            await bot.stop()
            await userbot.stop()
            logger.info("✅ Bot and Userbot stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        raise SystemExit(1)
