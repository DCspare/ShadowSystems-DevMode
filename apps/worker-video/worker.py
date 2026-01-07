import asyncio
import logging
import os
import subprocess
import time
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from handlers.leech import MediaLeecher
from handlers.downloader import downloader

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("VideoWorker")

class VideoWorker:
    """
    Main Service for StreamVault Video Processing.
    """
    def __init__(self):
        self.app = None
        self.db = None
        self.redis = None
        self.leecher = None
        self.worker_id = os.getenv("WORKER_ID", "video_worker_1")
        # Ensure log_channel is int
        try:
            self.log_channel = int(os.getenv("TG_LOG_CHANNEL_ID"))
        except:
            self.log_channel = 0

    def start_aria2_daemon(self):
        """Starts the aria2c binary."""
        logger.info("🚀 Launching Aria2 RPC Daemon...")
        try:
            command = [
                "aria2c",
                "--enable-rpc",
                "--rpc-listen-all=false", 
                "--rpc-allow-origin-all",
                "--dir=/app/downloads",
                "--max-connection-per-server=16",
                "--quiet"
            ]
            self.aria2_proc = subprocess.Popen(command)
            time.sleep(2)
            
            if self.aria2_proc.poll() is None:
                logger.info("✅ Aria2 Daemon is running.")
            else:
                logger.error("❌ Aria2 Daemon failed to start!")
                exit(1)
        except Exception as e:
            logger.error(f"Failed to start Aria2: {e}")
            exit(1)

    async def init_services(self):
        # 1. DB
        mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
        self.db = mongo_client["shadow_systems"]
        self.redis = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        
        # 2. Downloader
        self.start_aria2_daemon()
        await downloader.initialize()

        # 3. Telegram Init
        logger.info("Initializing Pyrogram Client...")
        is_bot_mode = os.getenv("WORKER_MODE", "BOT") == "BOT"
        
        if is_bot_mode:
            self.app = Client(
                name="worker_bot",
                api_id=int(os.getenv("TG_API_ID")),
                api_hash=os.getenv("TG_API_HASH"),
                bot_token=os.getenv("TG_WORKER_BOT_TOKEN"),
                workdir="/app/sessions" 
            )
        else:
            session_name = os.getenv("SESSION_FILE", "worker_default")
            self.app = Client(
                name=session_name,
                api_id=int(os.getenv("TG_API_ID")),
                api_hash=os.getenv("TG_API_HASH"),
                workdir="/app/sessions"
            )

        # ---------------------------------------------
        # MANUAL HEALTH CHECK COMMAND (The New Fix)
        # ---------------------------------------------
        @self.app.on_message(filters.command("health"))
        async def health_check(client, message):
            """Manual trigger to verify bot is alive and caching works"""
            # Collect Stats
            uptime = "Online"
            mode = "BOT MODE" if is_bot_mode else "USER MODE"
            
            chat_info = f"{message.chat.title} (`{message.chat.id}`)"

            # Send simpler format to ensure rendering
            await message.reply_text(
              f"🤖 **Shadow Worker Status**\n\n"
              f"🆔 **Worker:** `{self.worker_id}`\n"
              f"🛡️ **Mode:** {mode}\n"
              f"📡 **Connected Peer:** {chat_info}\n\n"
              f"✅ **System Ready.**"
             )
            logger.info(f"Health Check command received from {message.chat.title}")

        # 4. Start
        await self.app.start()
        
        # 5. Safe Peer Resolution
        # We try to get_chat. If it fails, we rely on the manual /health command 
        # to "Wake up" the caching layer later.
        try:
            logger.info(f"�� Probing Channel {self.log_channel}...")
            chat = await self.app.get_chat(self.log_channel)
            logger.info(f"✅ Connection Established: {chat.title}")
            
            # Send Startup Signal
            await self.app.send_message(
                self.log_channel, 
                f"🔄 **Worker Restarted**\nready as: {self.worker_id}"
            )
        except Exception as e:
            logger.warning(f"⚠️ Automatic Handshake failed: {e}")
            logger.warning("👉 ACTION: Send '/health' in the Log Channel/Group to fix cache!")

        self.leecher = MediaLeecher(self.app, self.db)
        logger.info(f"Worker fully operational as @{(await self.app.get_me()).username}")

    async def task_watcher(self):
        """Watch Redis"""
        logger.info("Task Watcher started. Listening to 'queue:leech'...")
        while True:
            try:
                task = await self.redis.brpop("queue:leech", timeout=30)
                if task:
                    payload = task[1]
                    logger.info(f"Consumed task: {payload}")
                    try:
                        tmdb_id, raw_url = payload.split("|")
                        info = downloader.get_direct_url(raw_url)
                        local_path = await downloader.start_download(info['url'])
                        
                        if os.path.exists(local_path):
                            await self.leecher.upload_and_sync(local_path, int(tmdb_id))
                            os.remove(local_path)
                            logger.info(f"🗑️ Cleaned up: {local_path}")
                        else:
                            logger.error("Download ghosted.")
                    except Exception as e:
                        logger.error(f"Task Payload Error: {e}")
            except Exception as e:
                logger.error(f"Loop Error: {e}")
                await asyncio.sleep(2)

async def main():
    worker = VideoWorker()
    try:
        await worker.init_services()
        await worker.task_watcher()
    except KeyboardInterrupt:
        if hasattr(worker, 'aria2_proc'):
            worker.aria2_proc.terminate()

if __name__ == "__main__":
    asyncio.run(main())
