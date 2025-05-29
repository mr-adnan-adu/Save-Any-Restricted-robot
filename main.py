# main.py - Fixed version for Render deployment
import logging
import re
import asyncio
import sqlite3
import os
import json
from typing import List, Optional, Tuple, Union
from datetime import datetime, timedelta
from aiohttp import web, ClientSession
import threading

from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError, 
    FloodWaitError,
    ChatAdminRequiredError,
    MessageNotModifiedError
)

# Configure logging for cloud deployment
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Console output for Render logs
    ]
)
logger = logging.getLogger(__name__)

class TelegramUserbot:
    def __init__(self):
        # Get credentials from environment variables
        self.api_id = int(os.getenv('API_ID', '0'))
        self.api_hash = os.getenv('API_HASH', '')
        self.phone_number = os.getenv('PHONE_NUMBER', '')
        self.session_string = os.getenv('SESSION_STRING', '')
        
        # Validate credentials
        if not all([self.api_id, self.api_hash, self.phone_number]):
            raise ValueError("Missing required environment variables: API_ID, API_HASH, PHONE_NUMBER")
        
        # Use session string if available, otherwise create new session
        if self.session_string:
            from telethon.sessions import StringSession
            session = StringSession(self.session_string)
        else:
            session = 'userbot_session'
        
        self.client = TelegramClient(session, self.api_id, self.api_hash)
        self.db_path = "/tmp/userbot_data.db" if os.path.exists('/tmp') else "userbot_data.db"
        self.downloads_path = "/tmp/downloads" if os.path.exists('/tmp') else "downloads"
        self.rate_limit_delay = 1
        self.last_operation_time = datetime.now()
        self.start_time = datetime.now()
        
        # Create downloads directory
        os.makedirs(self.downloads_path, exist_ok=True)
        
        self._setup_database()
        self._setup_handlers()
    
    def _setup_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_chat_id INTEGER,
                    source_msg_id INTEGER,
                    target_chat_id INTEGER,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS userbot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_check (
                    last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'healthy'
                )
            """)
            conn.commit()
    
    def _setup_handlers(self):
        """Setup userbot event handlers"""
        
        @self.client.on(events.NewMessage(pattern=r'^\.help$'))
        async def help_handler(event):
            help_text = """
🤖 **Userbot Commands (Cloud Deployed):**

**Basic Commands:**
• `.help` - Show this help
• `.stats` - Show processing statistics
• `.health` - Check bot health
• `.ping` - Test bot responsiveness

**Link Processing:**
• `.forward <links>` - Forward messages from links
• `.copy <links>` - Copy messages without forward tag
• `.download <links>` - Download media from links

**Supported Link Formats:**
• `https://t.me/c/123456789/100`
• `https://t.me/username/100`
• `t.me/c/123456789/100-200` (range)
• `-100123456789/100` (chat ID format)

**Cloud Features:**
• `.session` - Get current session string
• `.restart` - Restart bot (admin only)

**Settings:**
• `.delay <seconds>` - Set delay between operations

**Deploy Status:**
🌐 Deployed on Render
📍 Server Location: Cloud
⚡ Auto-restart enabled
            """
            await event.reply(help_text)
        
        @self.client.on(events.NewMessage(pattern=r'^\.ping$'))
        async def ping_handler(event):
            start_time = datetime.now()
            msg = await event.reply("🏃‍♂️ Pinging...")
            end_time = datetime.now()
            latency = (end_time - start_time).total_seconds() * 1000
            
            await msg.edit(f"🏓 **Pong!**\n"
                          f"⚡ Latency: {latency:.2f}ms\n"
                          f"🌐 Status: Online\n"
                          f"📅 Uptime: {self._get_uptime()}")
        
        @self.client.on(events.NewMessage(pattern=r'^\.health$'))
        async def health_handler(event):
            await self._health_check(event)
        
        @self.client.on(events.NewMessage(pattern=r'^\.session$'))
        async def session_handler(event):
            # Only allow in private chat for security
            if event.is_private:
                try:
                    session_string = self.client.session.save()
                    await event.reply(
                        f"🔐 **Session String:**\n"
                        f"```\n{session_string}\n```\n\n"
                        f"⚠️ **Keep this secure!** Save it as SESSION_STRING environment variable.",
                        parse_mode='markdown'
                    )
                except Exception as e:
                    await event.reply(f"❌ Error getting session: {str(e)}")
            else:
                await event.reply("❌ Session string only available in private chat!")
        
        @self.client.on(events.NewMessage(pattern=r'^\.stats$'))
        async def stats_handler(event):
            await self._show_statistics(event)
        
        @self.client.on(events.NewMessage(pattern=r'^\.forward (.+)'))
        async def forward_handler(event):
            links = event.pattern_match.group(1)
            await self._process_links(event, links, action='forward')
        
        @self.client.on(events.NewMessage(pattern=r'^\.copy (.+)'))
        async def copy_handler(event):
            links = event.pattern_match.group(1)
            await self._process_links(event, links, action='copy')
        
        @self.client.on(events.NewMessage(pattern=r'^\.download (.+)'))
        async def download_handler(event):
            links = event.pattern_match.group(1)
            await self._process_links(event, links, action='download')
        
        @self.client.on(events.NewMessage(pattern=r'^\.delay (\d+)'))
        async def delay_handler(event):
            delay = int(event.pattern_match.group(1))
            self.rate_limit_delay = delay
            await self._save_setting('rate_limit_delay', str(delay))
            await event.reply(f"✅ Delay set to {delay} seconds")
    
    def _get_uptime(self) -> str:
        """Calculate uptime since start"""
        uptime = datetime.now() - self.start_time
        return str(uptime).split('.')[0]
    
    async def _health_check(self, event):
        """Comprehensive health check"""
        health_info = {
            'database': 'Unknown',
            'storage': 'Unknown',
            'memory': 'Unknown',
            'network': 'Unknown'
        }
        
        # Database check
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
                health_info['database'] = '✅ Healthy'
        except Exception as e:
            health_info['database'] = f'❌ Error: {str(e)[:50]}'
        
        # Storage check
        try:
            if os.path.exists(self.downloads_path):
                files = len(os.listdir(self.downloads_path))
                health_info['storage'] = f'✅ {files} files'
            else:
                health_info['storage'] = '⚠️ Directory not found'
        except:
            health_info['storage'] = '⚠️ Unable to check'
        
        # Memory check (if available)
        try:
            import psutil
            memory = psutil.virtual_memory()
            health_info['memory'] = f'✅ {memory.percent}% used'
        except:
            health_info['memory'] = '⚠️ psutil not available'
        
        # Network check
        try:
            await self.client.get_me()
            health_info['network'] = '✅ Connected'
        except Exception as e:
            health_info['network'] = f'❌ {str(e)[:50]}'
        
        # Update health check timestamp
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO health_check (last_ping, status) VALUES (datetime('now'), 'healthy')"
            )
            conn.commit()
        
        health_text = f"""
🏥 **Health Check Report**

💾 Database: {health_info['database']}
📁 Storage: {health_info['storage']}
🧠 Memory: {health_info['memory']}
🌐 Network: {health_info['network']}

⏰ Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 Uptime: {self._get_uptime()}
📍 Environment: Cloud (Render)
        """
        
        await event.reply(health_text)
    
    async def _rate_limit(self):
        """Implement rate limiting"""
        now = datetime.now()
        time_since_last = (now - self.last_operation_time).total_seconds()
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_operation_time = datetime.now()
    
    def _parse_telegram_links(self, text: str) -> List[Tuple[Union[int, str], List[int]]]:
        """Parse various Telegram link formats with improved validation"""
        results = []
        
        # Pattern 1: https://t.me/c/chat_id/msg_id or range
        pattern1 = r'(?:https?://)?t\.me/c/(-?\d+)/(\d+)(?:-(\d+))?'
        for match in re.finditer(pattern1, text):
            chat_id = int(match.group(1))
            # Convert to proper chat ID format
            if chat_id > 0:
                chat_id = int(f"-100{chat_id}")
            start_msg = int(match.group(2))
            end_msg = int(match.group(3)) if match.group(3) else start_msg
            msg_ids = list(range(start_msg, min(end_msg + 1, start_msg + 50)))  # Limit for cloud
            results.append((chat_id, msg_ids))
        
        # Pattern 2: https://t.me/username/msg_id or range
        pattern2 = r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)/(\d+)(?:-(\d+))?'
        for match in re.finditer(pattern2, text):
            username = match.group(1)
            # Skip if username is just 'c' (common error)
            if username.lower() == 'c':
                continue
            start_msg = int(match.group(2))
            end_msg = int(match.group(3)) if match.group(3) else start_msg
            msg_ids = list(range(start_msg, min(end_msg + 1, start_msg + 50)))
            results.append((username, msg_ids))
        
        # Pattern 3: Chat ID format (-100xxxxxxxxx/msg_id)
        pattern3 = r'(-100\d+)/(\d+)(?:-(\d+))?'
        for match in re.finditer(pattern3, text):
            chat_id = int(match.group(1))
            start_msg = int(match.group(2))
            end_msg = int(match.group(3)) if match.group(3) else start_msg
            msg_ids = list(range(start_msg, min(end_msg + 1, start_msg + 50)))
            results.append((chat_id, msg_ids))
        
        return results
    
    async def _resolve_chat_id(self, chat_identifier: Union[str, int]) -> int:
        """Resolve username or chat ID to actual chat ID with better error handling"""
        try:
            if isinstance(chat_identifier, str):
                # Skip obviously invalid identifiers
                if chat_identifier.lower() in ['c', '', ' ']:
                    raise ValueError(f"Invalid chat identifier: '{chat_identifier}'")
                entity = await self.client.get_entity(chat_identifier)
                return entity.id
            return chat_identifier
        except Exception as e:
            logger.error(f"Failed to resolve chat {chat_identifier}: {e}")
            raise ValueError(f"Cannot find chat: {chat_identifier}")
    
    async def _process_links(self, event, links_text: str, action: str = 'forward'):
        """Process links with cloud optimizations and better error handling"""
        try:
            parsed_links = self._parse_telegram_links(links_text)
            
            if not parsed_links:
                await event.reply("❌ No valid links found! Use format like:\n"
                                "• `https://t.me/c/123456789/100`\n"
                                "• `https://t.me/username/100`\n"
                                "• `-100123456789/100`")
                return
            
            status_msg = await event.reply(f"🔄 Processing {len(parsed_links)} link(s) on cloud...")
            
            success_count = 0
            error_count = 0
            
            for chat_identifier, msg_ids in parsed_links:
                try:
                    source_chat_id = await self._resolve_chat_id(chat_identifier)
                    target_chat_id = event.chat_id
                    
                    for msg_id in msg_ids:
                        try:
                            await self._rate_limit()
                            
                            if action == 'forward':
                                await self._forward_message(source_chat_id, msg_id, target_chat_id)
                            elif action == 'copy':
                                await self._copy_message(source_chat_id, msg_id, target_chat_id)
                            elif action == 'download':
                                await self._download_message_media(source_chat_id, msg_id)
                            
                            success_count += 1
                            
                            # Log to database
                            with sqlite3.connect(self.db_path) as conn:
                                conn.execute("""
                                    INSERT INTO processed_links 
                                    (source_chat_id, source_msg_id, target_chat_id, status)
                                    VALUES (?, ?, ?, ?)
                                """, (source_chat_id, msg_id, target_chat_id, 'success'))
                                conn.commit()
                        
                        except FloodWaitError as e:
                            wait_time = min(e.seconds, 300)  # Max 5 minutes wait
                            await event.reply(f"⚠️ Rate limited. Waiting {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        except Exception as e:
                            logger.error(f"Failed to process message {msg_id}: {e}")
                            error_count += 1
                
                except Exception as e:
                    logger.error(f"Failed to process chat {chat_identifier}: {e}")
                    await event.reply(f"❌ Error with chat {chat_identifier}: {str(e)}")
                    error_count += len(msg_ids)
            
            result_text = f"✅ **Cloud Processing Complete**\n" \
                         f"✅ Success: {success_count}\n" \
                         f"❌ Errors: {error_count}\n" \
                         f"🌐 Server: Render"
            
            try:
                await status_msg.edit(result_text)
            except MessageNotModifiedError:
                await event.reply(result_text)
        
        except Exception as e:
            logger.error(f"Error in _process_links: {e}")
            await event.reply(f"❌ Cloud Error: {str(e)}")
    
    async def _forward_message(self, source_chat_id: int, msg_id: int, target_chat_id: int):
        """Forward a message"""
        try:
            message = await self.client.get_messages(source_chat_id, ids=msg_id)
            if message:
                await self.client.forward_messages(target_chat_id, message)
        except Exception as e:
            logger.error(f"Failed to forward message {msg_id}: {e}")
            raise
    
    async def _copy_message(self, source_chat_id: int, msg_id: int, target_chat_id: int):
        """Copy a message without forward tag"""
        try:
            message = await self.client.get_messages(source_chat_id, ids=msg_id)
            if message:
                if message.media:
                    await self.client.send_file(
                        target_chat_id,
                        message.media,
                        caption=message.text or ""
                    )
                else:
                    await self.client.send_message(target_chat_id, message.text or "")
        except Exception as e:
            logger.error(f"Failed to copy message {msg_id}: {e}")
            raise
    
    async def _download_message_media(self, source_chat_id: int, msg_id: int):
        """Download media with cloud storage"""
        try:
            message = await self.client.get_messages(source_chat_id, ids=msg_id)
            if message and message.media:
                filename = await self.client.download_media(message, self.downloads_path)
                logger.info(f"Downloaded to cloud storage: {filename}")
                return filename
        except Exception as e:
            logger.error(f"Failed to download media from message {msg_id}: {e}")
            raise
    
    async def _save_setting(self, key: str, value: str):
        """Save a setting to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO userbot_settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            conn.commit()
    
    async def _get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM userbot_settings WHERE key = ?", (key,)
            )
            result = cursor.fetchone()
            return result[0] if result else default
    
    async def _show_statistics(self, event):
        """Show comprehensive cloud statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as errors
                FROM processed_links
                WHERE processed_at > datetime('now', '-24 hours')
            """)
            stats = cursor.fetchone()
            
            # Get file count in downloads
            try:
                download_count = len(os.listdir(self.downloads_path))
            except:
                download_count = 0
            
            stats_text = f"""
📊 **Cloud Userbot Statistics (24h)**

✅ Total Processed: {stats[0] or 0}
✅ Successful: {stats[1] or 0}  
❌ Errors: {stats[2] or 0}
📁 Downloads: {download_count} files

⚙️ **Current Settings:**
• Rate Limit: {self.rate_limit_delay}s

🌐 **Cloud Environment:**
• Platform: Render
• Database: {self.db_path}
• Storage: {self.downloads_path}
• Uptime: {self._get_uptime()}
            """
            
            await event.reply(stats_text)
    
    async def start(self):
        """Start the userbot with cloud optimizations"""
        try:
            # Connect to Telegram
            await self.client.start(phone=self.phone_number)
            
            # Load saved settings
            saved_delay = await self._get_setting('rate_limit_delay')
            if saved_delay:
                self.rate_limit_delay = int(saved_delay)
            
            me = await self.client.get_me()
            logger.info(f"Cloud userbot started as {me.username or me.first_name}")
            
            # Send startup notification
            try:
                await self.client.send_message('me', 
                    "🌐 **Cloud Userbot Started Successfully!**\n\n"
                    f"📍 Deployed on: Render\n"
                    f"⚡ Status: Online\n"
                    f"🔧 Rate Limit: {self.rate_limit_delay}s\n"
                    f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    "Type `.help` for available commands.\n"
                    "Type `.health` to check system status."
                )
            except:
                pass  # Don't fail if we can't send startup message
            
            return True
            
        except SessionPasswordNeededError:
            logger.error("Two-factor authentication required. Set up session string.")
            return False
        except Exception as e:
            logger.error(f"Failed to start cloud userbot: {e}")
            return False
    
    async def run(self):
        """Run the userbot with cloud keep-alive"""
        if await self.start():
            logger.info("Cloud userbot is running...")
            
            # Keep-alive mechanism for cloud deployment
            async def keep_alive():
                while True:
                    try:
                        await asyncio.sleep(300)  # 5 minutes
                        await self.client.get_me()  # Simple API call to stay active
                        logger.info("Keep-alive ping successful")
                    except Exception as e:
                        logger.error(f"Keep-alive failed: {e}")
            
            # Run keep-alive in background
            asyncio.create_task(keep_alive())
            
            try:
                await self.client.run_until_disconnected()
            except KeyboardInterrupt:
                logger.info("Cloud userbot stopped")
            finally:
                await self.client.disconnect()
        else:
            logger.error("Failed to start cloud userbot")

# HTTP Server for Render port requirement
async def create_http_server():
    """Create a simple HTTP server to satisfy Render's port requirement"""
    
    async def health_check(request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "telegram-userbot"
        })
    
    async def status(request):
        """Status endpoint"""
        return web.json_response({
            "status": "running",
            "uptime": str(datetime.now() - start_time).split('.')[0],
            "service": "telegram-userbot",
            "version": "1.0.0"
        })
    
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', status)
    
    # Get port from environment (Render provides this)
    port = int(os.getenv('PORT', 8080))
    
    return app, port

# Global start time for uptime calculation
start_time = datetime.now()

# Main entry point for cloud deployment
async def main():
    """Main function optimized for cloud deployment"""
    logger.info("Initializing cloud userbot...")
    
    try:
        # Create HTTP server for Render
        app, port = await create_http_server()
        
        # Start HTTP server in background
        async def start_http_server():
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            logger.info(f"HTTP server started on port {port}")
        
        # Start HTTP server
        await start_http_server()
        
        # Start userbot
        userbot = TelegramUserbot()
        await userbot.run()
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set the required environment variables in Render dashboard")
    except Exception as e:
        logger.error(f"Cloud userbot crashed: {e}")
        # In cloud environment, we want to restart on crash
        await asyncio.sleep(10)  # Wait before restart
        await main()  # Restart

if __name__ == "__main__":
    # Run the cloud userbot
    asyncio.run(main())
