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

    def clean_slate(self):
        """🧹 WIPER: Removes all stale files from previous crashes"""
        dl_dir = "/app/downloads"
        logger.info(f"🧹 Cleaning slate at: {dl_dir}")
        if os.path.exists(dl_dir):
            try:
                # Remove all files in the directory
                for filename in os.listdir(dl_dir):
                    file_path = os.path.join(dl_dir, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                logger.info("✅ Downloads folder purged.")
            except Exception as e:
                logger.warning(f"Failed to clean download folder: {e}")
        else:
            os.makedirs(dl_dir, exist_ok=True)

    def start_aria2_daemon(self):
        """Starts the aria2c binary."""
        logger.info("🚀 Launching Aria2 RPC Daemon...")
        
        # FIX: Force explicit path relative to root
        dl_path = "/app/downloads"
        if not os.path.exists(dl_path):
            os.makedirs(dl_path, exist_ok=True)

        try:
            command = [
                "aria2c",
                "--enable-rpc",
                "--rpc-listen-all=false", 
                "--rpc-allow-origin-all",
                f"--dir={dl_path}",
                
                # CRITICAL FIXES FOR ERR 16 / ABORT
                "--file-allocation=none",       # Stop pre-allocating disk space (Fixes Docker Error)
                "--disk-cache=0",               # Disable RAM caching (Prevent buffer lag)
                "--max-connection-per-server=4",# Keep connections low to avoid Google/Host blocks
                "--min-split-size=10M",
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
        # 0. Safety Cleanup
        self.clean_slate()
        
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
             # FORCE CACHE UPDATE
            # self.log_channel = message.chat.id
            logger.info(f"Health Check successful. Session validated. Chat: {message.chat.title}")

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
                        # 🔁 FLEXIBLE SPLIT (Supports 3 or 4 args)
                        parts = payload.split("|")
                        tmdb_id = parts[0]
                        raw_url = parts[1]
                        type_hint = parts[2] if len(parts) > 2 else "auto"
                        name_hint = parts[3] if len(parts) > 3 else ""

                        # 1. Download
                        target_info = downloader.get_direct_url(raw_url)
                        local_path = await downloader.start_download(target_info)
                        
                        if local_path and os.path.exists(local_path):
                            
                            # 🔄 RENAME LOGIC (The Fix for PTN)
                            if name_hint:
                                dir_name = os.path.dirname(local_path)
                                ext = os.path.splitext(local_path)[1]
                                new_filename = f"{name_hint}{ext}"
                                new_path = os.path.join(dir_name, new_filename)
                                
                                logger.info(f"✏️ Renaming: {os.path.basename(local_path)} -> {new_filename}")
                                os.rename(local_path, new_path)
                                local_path = new_path

                            # 2. Upload with Hint
                            await self.leecher.upload_and_sync(
                                local_path, 
                                int(tmdb_id),
                                type_hint=type_hint
                            )

                            # 3. Clean
                            if os.path.isfile(local_path):
                                os.remove(local_path)
                            logger.info(f"🗑️ Cleaned up: {local_path}")
                        else:
                            logger.error("Download ghosted.")

                    except Exception as e:
                        logger.error(f"Task Payload Error: {e}")
                        await asyncio.sleep(2)

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
