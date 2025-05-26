from pyrogram import Client, filters, idle
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChatAdminRequired, UserNotParticipant, ChannelPrivate, PeerIdInvalid
import asyncio
import os
import logging
from datetime import datetime, timedelta
import json
import time
from aiohttp import web
import re
import warnings
from typing import Dict, Optional, Tuple, Any
import traceback

# Suppress asyncio task warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited.*")

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
def load_config() -> Dict[str, Any]:
    """Load and validate configuration from environment variables"""
    config = {
        'API_ID': os.environ.get("API_ID"),
        'API_HASH': os.environ.get("API_HASH"),
        'BOT_TOKEN': os.environ.get("BOT_TOKEN"),
        'SESSION_STRING': os.environ.get("SESSION_STRING") or os.environ.get("USERBOT_SESSION_STRING"),
        'OWNER_ID': os.environ.get("OWNER_ID"),
        'MAX_MESSAGES': int(os.environ.get("MAX_MESSAGES", "20")),
        'RATE_LIMIT': int(os.environ.get("RATE_LIMIT_SECONDS", "3")),
        'ADMIN_RATE_LIMIT': int(os.environ.get("ADMIN_RATE_LIMIT", "1")),
        'MAX_FILE_SIZE': int(os.environ.get("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024,  # Convert MB to bytes
        'AUTHORIZED_USERS': os.environ.get("AUTHORIZED_USERS", "").split(',') if os.environ.get("AUTHORIZED_USERS") else []
    }
    
    # Validate required fields
    required_fields = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'SESSION_STRING']
    missing_fields = [field for field in required_fields if not config[field]]
    
    if missing_fields:
        logger.error(f"Missing required environment variables: {missing_fields}")
        available_vars = [key for key in os.environ.keys() if any(term in key.upper() for term in ['API', 'BOT', 'SESSION', 'TOKEN', 'HASH'])]
        logger.info(f"Available environment variables: {available_vars}")
        raise ValueError(f"Missing required environment variables: {missing_fields}")
    
    try:
        config['API_ID'] = int(config['API_ID'])
        config['OWNER_ID'] = int(config['OWNER_ID']) if config['OWNER_ID'] else None
        config['AUTHORIZED_USERS'] = [int(uid.strip()) for uid in config['AUTHORIZED_USERS'] if uid.strip().isdigit()]
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
    logger.info(f"AUTHORIZED_USERS: {len(config['AUTHORIZED_USERS'])} users")
    
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
chat_cache = {}  # Cache for resolved chats

def update_user_stats(user_id: int, success: bool = True) -> None:
    """Update user statistics"""
    if user_id not in user_stats:
        user_stats[user_id] = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'first_seen': datetime.now(),
            'last_seen': datetime.now(),
            'bytes_transferred': 0
        }
    
    user_stats[user_id]['total_requests'] += 1
    user_stats[user_id]['last_seen'] = datetime.now()
    
    if success:
        user_stats[user_id]['successful_requests'] += 1
    else:
        user_stats[user_id]['failed_requests'] += 1

def is_rate_limited(user_id: int) -> Tuple[bool, int]:
    """Check if user is rate limited"""
    now = datetime.now()
    rate_limit = CONFIG['ADMIN_RATE_LIMIT'] if is_owner_or_authorized(user_id) else CONFIG['RATE_LIMIT']
    
    if user_id in user_last_request:
        time_diff = now - user_last_request[user_id]
        if time_diff < timedelta(seconds=rate_limit):
            return True, rate_limit - time_diff.seconds
    user_last_request[user_id] = now
    return False, 0

def is_owner(user_id: int) -> bool:
    """Check if user is bot owner"""
    return CONFIG['OWNER_ID'] and user_id == CONFIG['OWNER_ID']

def is_owner_or_authorized(user_id: int) -> bool:
    """Check if user is owner or authorized"""
    return is_owner(user_id) or user_id in CONFIG['AUTHORIZED_USERS']

async def handle_flood_wait(e: FloodWait) -> None:
    """Handle Telegram flood wait errors"""
    wait_time = e.value if hasattr(e, 'value') else 60
    logger.warning(f"Flood wait: {wait_time} seconds")
    await asyncio.sleep(wait_time)

def parse_telegram_link(link: str) -> Optional[Dict[str, Any]]:
    """Enhanced link parsing with better validation"""
    link = link.strip()
    
    # Patterns for different link formats
    private_link_pattern = r'https://t\.me/c/(\d+)/(\d+)(?:-(\d+))?'
    public_link_pattern = r'https://t\.me/([^/]+)/(\d+)(?:-(\d+))?'
    
    # Try private link first
    match = re.match(private_link_pattern, link)
    if match:
        channel_id_part = match.group(1)
        start_msg = int(match.group(2))
        end_msg = int(match.group(3)) if match.group(3) else None
        chat_id = int("-100" + channel_id_part)
        
        return {
            'type': 'private',
            'chat_id': chat_id,
            'start_msg': start_msg,
            'end_msg': end_msg,
            'is_range': end_msg is not None
        }
    
    # Try public link
    match = re.match(public_link_pattern, link)
    if match:
        username = match.group(1)
        start_msg = int(match.group(2))
        end_msg = int(match.group(3)) if match.group(3) else None
        
        return {
            'type': 'public',
            'chat_id': username,
            'start_msg': start_msg,
            'end_msg': end_msg,
            'is_range': end_msg is not None
        }
    
    return None

async def resolve_chat_with_cache(client: Client, chat_id) -> Any:
    """Resolve chat with caching to improve performance"""
    cache_key = str(chat_id)
    
    # Check cache first
    if cache_key in chat_cache:
        cached_time, chat_info = chat_cache[cache_key]
        # Cache valid for 1 hour
        if datetime.now() - cached_time < timedelta(hours=1):
            logger.info(f"Using cached chat info for {chat_id}")
            return chat_info
    
    # Resolve chat
    try:
        chat_info = await client.get_chat(chat_id)
        # Cache the result
        chat_cache[cache_key] = (datetime.now(), chat_info)
        logger.info(f"Resolved and cached chat: {chat_info.title}")
        return chat_info
        
    except (PeerIdInvalid, KeyError, ValueError):
        # Try searching in dialogs
        logger.info(f"Searching for chat {chat_id} in dialogs...")
        async for dialog in client.get_dialogs():
            if dialog.chat.id == chat_id:
                chat_info = dialog.chat
                chat_cache[cache_key] = (datetime.now(), chat_info)
                logger.info(f"Found and cached from dialogs: {chat_info.title}")
                return chat_info
        
        raise PeerIdInvalid(f"Cannot resolve peer {chat_id}")

async def fetch_and_send_message(chat_id, msg_id: int, message: Message, reply_to_msg_id: Optional[int] = None) -> bool:
    """Enhanced message fetching with better error handling"""
    try:
        logger.info(f"Fetching message {msg_id} from chat {chat_id}")
        
        # Resolve chat
        try:
            chat_info = await resolve_chat_with_cache(userbot, chat_id)
            logger.info(f"Chat resolved: {chat_info.title} (ID: {chat_info.id})")
        except ChannelPrivate:
            await message.reply("❌ Private channel - userbot needs access", reply_to_message_id=reply_to_msg_id)
            return False
        except UserNotParticipant:
            await message.reply("❌ Userbot not a member of this channel", reply_to_message_id=reply_to_msg_id)
            return False
        except PeerIdInvalid:
            await message.reply(f"❌ Cannot access chat. Try `/preload {chat_id}`", reply_to_message_id=reply_to_msg_id)
            return False
        except Exception as e:
            logger.error(f"Chat resolution error: {e}")
            await message.reply(f"❌ Chat access error: {str(e)[:50]}", reply_to_message_id=reply_to_msg_id)
            return False
        
        # Get the message
        msg = await userbot.get_messages(chat_id, msg_id)
        
        if not msg:
            await message.reply(f"⚠️ Message {msg_id} not found", reply_to_message_id=reply_to_msg_id)
            return False
        
        # Handle different message types
        if msg.text or msg.caption:
            content = msg.text or msg.caption
            if len(content) > 4096:
                # Split long messages
                for i in range(0, len(content), 4096):
                    chunk = content[i:i+4096]
                    await message.reply(chunk, reply_to_message_id=reply_to_msg_id)
                    await asyncio.sleep(0.5)
            else:
                await message.reply(content, reply_to_message_id=reply_to_msg_id)
                
        elif msg.media:
            caption = msg.caption or ""
            
            # Check file size for documents
            if msg.document and msg.document.file_size > CONFIG['MAX_FILE_SIZE']:
                size_mb = msg.document.file_size / (1024 * 1024)
                max_mb = CONFIG['MAX_FILE_SIZE'] / (1024 * 1024)
                await message.reply(f"⚠️ File too large: {size_mb:.1f}MB (max: {max_mb}MB)", reply_to_message_id=reply_to_msg_id)
                return False
            
            try:
                if msg.document:
                    await message.reply_document(msg.document.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                elif msg.photo:
                    await message.reply_photo(msg.photo.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                elif msg.video:
                    await message.reply_video(msg.video.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                elif msg.audio:
                    await message.reply_audio(msg.audio.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                elif msg.voice:
                    await message.reply_voice(msg.voice.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                elif msg.video_note:
                    await message.reply_video_note(msg.video_note.file_id, reply_to_message_id=reply_to_msg_id)
                elif msg.sticker:
                    await message.reply_sticker(msg.sticker.file_id, reply_to_message_id=reply_to_msg_id)
                elif msg.animation:
                    await message.reply_animation(msg.animation.file_id, caption=caption, reply_to_message_id=reply_to_msg_id)
                else:
                    await message.reply("⚠️ Unsupported media type", reply_to_message_id=reply_to_msg_id)
                    return False
                    
            except Exception as media_error:
                logger.error(f"Media send error: {media_error}")
                await message.reply(f"❌ Media error: {str(media_error)[:50]}", reply_to_message_id=reply_to_msg_id)
                return False
        else:
            await message.reply("⚠️ Empty message", reply_to_message_id=reply_to_msg_id)
            return False
            
        logger.info(f"✅ Message {msg_id} sent successfully")
        await asyncio.sleep(0.8)  # Prevent flooding
        return True
        
    except FloodWait as e:
        await handle_flood_wait(e)
        await message.reply(f"⏳ Rate limited - wait {e.value}s", reply_to_message_id=reply_to_msg_id)
        return False
        
    except Exception as e:
        logger.error(f"Message fetch error {msg_id}: {e}")
        error_msg = str(e)[:80] + "..." if len(str(e)) > 80 else str(e)
        await message.reply(f"❌ Error: {error_msg}", reply_to_message_id=reply_to_msg_id)
        return False

# Message handlers
@bot.on_message(filters.private & (filters.regex(r'https://t\.me/c/\d+/\d+') | filters.regex(r'https://t\.me/[^/]+/\d+')))
async def handle_message_link(_, message: Message):
    """Handle both private and public channel links"""
    user_id = message.from_user.id
    logger.info(f"Link request from user {user_id}: {message.from_user.first_name}")
    
    # Rate limiting
    is_limited, wait_time = is_rate_limited(user_id)
    if is_limited:
        await message.reply(f"⏳ Rate limited - wait {wait_time}s")
        update_user_stats(user_id, success=False)
        return
    
    try:
        link = message.text.strip()
        parsed = parse_telegram_link(link)
        
        if not parsed:
            await message.reply("❌ Invalid Telegram link format")
            update_user_stats(user_id, success=False)
            return
        
        chat_id = parsed['chat_id']
        start_msg = parsed['start_msg']
        end_msg = parsed['end_msg']
        is_range = parsed['is_range']
        
        logger.info(f"Parsed: chat={chat_id}, start={start_msg}, end={end_msg}, range={is_range}")

        # Handle message range or single message
        if is_range:
            if start_msg > end_msg:
                start_msg, end_msg = end_msg, start_msg
            
            message_count = end_msg - start_msg + 1
            max_allowed = CONFIG['MAX_MESSAGES'] * 2 if is_owner_or_authorized(user_id) else CONFIG['MAX_MESSAGES']
            
            if message_count > max_allowed:
                await message.reply(f"⚠️ Too many messages. Max: {max_allowed}")
                update_user_stats(user_id, success=False)
                return
            
            status_msg = await message.reply(f"📥 Fetching {message_count} messages ({start_msg}-{end_msg})...")
            
            successful = 0
            failed = 0
            
            for msg_id in range(start_msg, end_msg + 1):
                success = await fetch_and_send_message(chat_id, msg_id, message, reply_to_msg_id=status_msg.id)
                if success:
                    successful += 1
                else:
                    failed += 1
                
                # Progress update every 5 messages
                if (msg_id - start_msg + 1) % 5 == 0:
                    progress = f"📊 Progress: {msg_id - start_msg + 1}/{message_count} | ✅ {successful} | ❌ {failed}"
                    try:
                        await status_msg.edit_text(progress)
                    except:
                        pass
                    
                if msg_id < end_msg:
                    await asyncio.sleep(0.5)
            
            await status_msg.edit_text(f"✅ Completed: {successful} successful, {failed} failed")
            update_user_stats(user_id, success=True)
            
        else:
            success = await fetch_and_send_message(chat_id, start_msg, message)
            update_user_stats(user_id, success=success)
            
    except Exception as e:
        logger.error(f"Link processing error: {e}")
        await message.reply(f"⚠️ Error: {str(e)[:80]}")
        update_user_stats(user_id, success=False)

@bot.on_message(filters.private & filters.regex(r'https://t\.me/\+'))
async def handle_invite_link(_, message: Message):
    """Handle invite links"""
    user_id = message.from_user.id
    
    is_limited, wait_time = is_rate_limited(user_id)
    if is_limited:
        await message.reply(f"⏳ Wait {wait_time}s before joining")
        return
    
    invite_link = message.text.strip()
    logger.info(f"Invite from user {user_id}: {invite_link}")
    
    try:
        chat = await userbot.join_chat(invite_link)
        logger.info(f"✅ Joined: {chat.title} (ID: {chat.id})")
        await message.reply(f"✅ Joined: **{chat.title}**\nID: `{chat.id}`")
        update_user_stats(user_id, success=True)
        
    except FloodWait as e:
        await handle_flood_wait(e)
        await message.reply(f"⏳ Rate limited - try in {e.value}s")
        
    except Exception as e:
        logger.error(f"Join failed: {e}")
        await message.reply(f"❌ Join failed: {str(e)[:50]}")
        update_user_stats(user_id, success=False)

@bot.on_message(filters.private & filters.command("start"))
async def start_command(_, message: Message):
    """Start command with user info"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    is_authorized = is_owner_or_authorized(user_id)
    status_emoji = "👑" if is_owner(user_id) else "⭐" if is_authorized else "👤"
    
    welcome_text = f"""
🤖 **Enhanced Content Fetcher Bot**

{status_emoji} Hello **{user_name}**!

**📊 Status:** ✅ Online
**🆔 Your ID:** `{user_id}`
**⏰ Time:** `{datetime.now().strftime('%H:%M:%S')}`
**🔐 Access:** {"Owner" if is_owner(user_id) else "Authorized" if is_authorized else "Standard"}

**📝 Usage:**
• Send Telegram links to fetch content
• Private: `t.me/c/123456789/1`
• Public: `t.me/channel/1`
• Range: `t.me/c/123456789/1-5`

**⚡ Limits:**
• Rate: {CONFIG['ADMIN_RATE_LIMIT'] if is_authorized else CONFIG['RATE_LIMIT']}s between requests
• Messages: {CONFIG['MAX_MESSAGES'] * 2 if is_authorized else CONFIG['MAX_MESSAGES']} per request
• File size: {CONFIG['MAX_FILE_SIZE'] // (1024*1024)}MB max

**🔧 Commands:**
/help - Detailed help
/stats - Your statistics  
/test - System status
/preload - Fix peer errors

Ready to fetch content! 🚀
    """
    await message.reply(welcome_text)

@bot.on_message(filters.private & filters.command("stats"))
async def stats_command(_, message: Message):
    """User statistics"""
    user_id = message.from_user.id
    
    if user_id not in user_stats:
        await message.reply("📊 **Statistics**\n\nNo data yet. Start using the bot!")
        return
    
    stats = user_stats[user_id]
    success_rate = (stats['successful_requests'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0
    
    stats_text = f"""
📊 **Your Statistics**

**📈 Requests:**
• Total: {stats['total_requests']}
• Success: {stats['successful_requests']}
• Failed: {stats['failed_requests']}
• Rate: {success_rate:.1f}%

**📅 Activity:**
• First: {stats['first_seen'].strftime('%d/%m %H:%M')}
• Last: {stats['last_seen'].strftime('%d/%m %H:%M')}

**⚙️ Your Limits:**
• Rate: {CONFIG['ADMIN_RATE_LIMIT'] if is_owner_or_authorized(user_id) else CONFIG['RATE_LIMIT']}s
• Messages: {CONFIG['MAX_MESSAGES'] * 2 if is_owner_or_authorized(user_id) else CONFIG['MAX_MESSAGES']}
• Access: {"Authorized" if is_owner_or_authorized(user_id) else "Standard"}
    """
    await message.reply(stats_text)

@bot.on_message(filters.private & filters.command("test"))
async def test_command(_, message: Message):
    """System test"""
    user_id = message.from_user.id
    
    try:
        bot_me = await bot.get_me()
        bot_status = "✅ Online"
        
        try:
            userbot_me = await userbot.get_me()
            userbot_status = "✅ Connected"
            userbot_info = f"{userbot_me.first_name}"
        except Exception as e:
            userbot_status = f"❌ Error"
            userbot_info = "Offline"
        
        test_result = f"""
🧪 **System Test**

**🤖 Bot:** {bot_status}
**👤 Userbot:** {userbot_status} ({userbot_info})
**💾 Cache:** {len(chat_cache)} chats cached
**👥 Users:** {len(user_stats)} total users
**🔐 Your Access:** {"Owner" if is_owner(user_id) else "Authorized" if is_owner_or_authorized(user_id) else "Standard"}

**⚙️ Limits:**
• Rate: {CONFIG['RATE_LIMIT']}s (std) / {CONFIG['ADMIN_RATE_LIMIT']}s (auth)
• Messages: {CONFIG['MAX_MESSAGES']} per request
• File size: {CONFIG['MAX_FILE_SIZE'] // (1024*1024)}MB max

All systems operational! ✅
        """
        await message.reply(test_result)
        
    except Exception as e:
        await message.reply(f"❌ Test failed: {str(e)[:50]}")

@bot.on_message(filters.private & filters.command("help"))
async def help_command(_, message: Message):
    """Detailed help"""
    help_text = """
📖 **Detailed Help**

**🔗 Link Formats:**
• Single: `t.me/c/1234567890/456`
• Range: `t.me/c/1234567890/456-460`
• Public: `t.me/channel_name/456`

**📋 Supported Content:**
✅ Text messages
✅ Photos & Videos  
✅ Documents & Files
✅ Audio & Voice
✅ Stickers & GIFs

**⚠️ Limitations:**
• Rate limiting between requests
• File size limits apply
• Bot needs channel access
• Some content may be restricted

**🔧 Commands:**
• `/preload <chat_id>` - Fix access issues
• `/stats` - Your usage statistics
• `/test` - Check system status

**💡 Tips:**
• Use `/preload` for peer errors
• Private channels need userbot access
• Large ranges take time to process

**❓ Common Issues:**
• "Cannot access" → Use `/preload`
• "Peer invalid" → Try `/preload <chat_id>`  
• "Not found" → Message deleted
• "Rate limited" → Wait between requests

Need help? Contact support! 📞
    """
    await message.reply(help_text)

@bot.on_message(filters.private & filters.command("preload"))
async def preload_command(_, message: Message):
    """Preload chat command"""
    user_id = message.from_user.id
    
    is_limited, wait_time = is_rate_limited(user_id)
    if is_limited:
        await message.reply(f"⏳ Wait {wait_time}s")
        return
    
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.reply("❌ Usage: `/preload <chat_id>`\nExample: `/preload -1001234567890`")
            return
        
        chat_input = args[1]
        
        if chat_input.startswith('https://t.me/'):
            parsed = parse_telegram_link(chat_input)
            if not parsed:
                await message.reply("❌ Invalid link format")
                return
            chat_id = parsed['chat_id']
        else:
            try:
                chat_id = int(chat_input)
            except ValueError:
                chat_id = chat_input
        
        status_msg = await message.reply(f"🔄 Preloading: {chat_id}...")
        
        try:
            chat_info = await resolve_chat_with_cache(userbot, chat_id)
            await status_msg.edit_text(f"✅ Preloaded: **{chat_info.title}**\nID: `{chat_info.id}`")
            update_user_stats(user_id, success=True)
        except Exception as e:
            await status_msg.edit_text(f"❌ Failed: {str(e)[:50]}")
            update_user_stats(user_id, success=False)
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)[:50]}")

# Owner commands
@bot.on_message(filters.private & filters.command("admin") & filters.user(CONFIG['OWNER_ID'] or []))
async def admin_command(_, message: Message):
    """Admin panel"""
    total_users = len(user_stats)
    total_requests = sum(stats['total_requests'] for stats in user_stats.values())
    cached_chats = len(chat_cache)
    
    admin_text = f"""
👑 **Admin Panel**

**📊 Statistics:**
• Total Users: {total_users}
• Total Requests: {total_requests}
• Cached Chats: {cached_chats}
• Authorized Users: {len(CONFIG['AUTHORIZED_USERS'])}

**⚙️ System:**
• Max Messages: {CONFIG['MAX_MESSAGES']}
• Rate Limit: {CONFIG['RATE_LIMIT']}s
• File Size Limit: {CONFIG['MAX_FILE_SIZE'] // (1024*1024)}MB
• Cache Entries: {len(chat_cache)}

**🔧 Admin Commands:**
/broadcast <message> - Send to all users
/adduser <user_id> - Add authorized user
/removeuser <user_id> - Remove user
/clearcache - Clear chat cache
/userstats - Detailed user stats
    """
    await message.reply(admin_text)

# Run the bot
async def main():
    """Main function"""
    logger.info("🚀 Starting Enhanced Content Fetcher Bot...")
    
    try:
        # Start both clients
        await bot.start()
        await userbot.start()
        
        bot_me = await bot.get_me()
        userbot_me = await userbot.get_me()
        
        logger.info(f"✅ Bot started: @{bot_me.username}")
        logger.info(f"✅ Userbot connected: {userbot_me.first_name}")
        logger.info(f"🔐 Owner ID: {CONFIG['OWNER_ID']}")
        logger.info(f"👥 Authorized users: {len(CONFIG['AUTHORIZED_USERS'])}")
        logger.info("🎯 Bot is ready for requests!")
        
        # Keep the bot running
        await idle()
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("🔄 Shutting down...")
        await bot.stop()
        await userbot.stop()

if __name__ == "__main__":
    asyncio.run(main())
