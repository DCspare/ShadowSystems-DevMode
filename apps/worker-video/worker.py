# apps/worker-video/worker.py 
import os
import sys
import time
import asyncio
import logging
import subprocess
sys.path.append("/app/shared")
from redis.asyncio import Redis
from shared.settings import settings
from pyrogram import Client, filters
from handlers.downloader import downloader
from handlers.flow_ingest import MediaLeecher
from motor.motor_asyncio import AsyncIOMotorClient
from shared.utils import resolve_peers
from shared.registry import task_dict, task_dict_lock, MirrorStatus
from handlers.status_manager import StatusManager

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
        self.resolved_peers = set()
        # Identity via Env Var (e.g. video_1) or fallback
        self.worker_id = os.getenv("WORKER_ID", "worker_1")
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
        
        # 1. DB (Persistence Layer)
        mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = mongo_client["shadow_systems"]
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # 2. Telegram Identity
        logger.info("Initializing Pyrogram Client...")
        is_bot_mode = os.getenv("WORKER_MODE", "BOT") == "BOT"

        session_name = os.getenv("SESSION_FILE", "worker_default")

        client_args = {
            "api_id": settings.TG_API_ID,
            "api_hash": settings.TG_API_HASH,
            "workdir": "/app/sessions",
            "sleep_threshold": 60,               # MLTB Standard: Wait 60s max for flood
            "max_concurrent_transmissions": 10,  # MLTB Standard: 10 parallel chunks
        }
        
        if is_bot_mode:
            logger.info(f"🤖 Bot Mode Active: {session_name}")
            self.app = Client(
                name="worker_bot",
                bot_token=settings.TG_WORKER_BOT_TOKEN,
                **client_args 
            )
        else:
            logger.info(f"⚡ User Session Mode Active: {session_name}")
            self.app = Client(
                name=session_name,
                session_string=settings.TG_SESSION_STRING, # Support for Session String
                **client_args
            )

        # MLTB Performance Tuning: Cache increase
        self.app.max_message_cache_size = 15000
        
        # 3. Initialize Leecher
        self.leecher = MediaLeecher(self.app, self.db, self.redis)

        # 4. Initialize Downloader with THE BRIDGE
        self.start_aria2_daemon()
        await downloader.initialize(
            redis=self.redis
        )

        # --- UX POLISH: Peer Discovery Listener ---
        @self.app.on_message()
        async def auto_resolve_handler(client, message):
            target_ids = [settings.TG_LOG_CHANNEL_ID, settings.TG_BACKUP_CHANNEL_ID]
            if message.chat.id in target_ids:
                if message.chat.id not in self.resolved_peers:
                    self.resolved_peers.add(message.chat.id)
                    logger.info(f"🛰️ [Peer Discovery]: {message.chat.title} ({message.chat.id}) - Access Hash Cached.")

        # 5. Start App and resolve peer 
        await self.app.start()
        self.app.start_time = time.time() # For Uptime check
        logger.info(f"Worker fully operational as @{(await self.app.get_me()).username}")

        # 6. ✅ Official Shadow-Handshake (No more /health)
        await resolve_peers(self.app, [
            settings.TG_LOG_CHANNEL_ID, 
            settings.TG_BACKUP_CHANNEL_ID
        ])

        # 7. Start Status Manager Heartbeat
        self.status_mgr = StatusManager(self.app)
        asyncio.create_task(self.status_mgr.update_heartbeat()) # Background Loop

        # # ---------------------------------------------
        # # 6. MANUAL HEALTH CHECK COMMAND
        # # ---------------------------------------------
        # @self.app.on_message(filters.command("health"))
        # async def health_check(client, message):
        #     """Manual trigger to verify bot is alive and caching works"""
        #     # Collect Stats
        #     uptime = "Online"
        #     mode = "BOT MODE" if is_bot_mode else "USER MODE"
            
        #     chat_info = f"{message.chat.title} (`{message.chat.id}`)"

        #     # Send simpler format to ensure rendering
        #     await message.reply_text(
        #       f"🤖 **Shadow Worker Status**\n\n"
        #       f"🆔 **Worker:** `{self.worker_id}`\n"
        #       f"🛡️ **Mode:** {mode}\n"
        #       f"📡 **Connected Peer:** {chat_info}\n\n"
        #       f"✅ **System Ready.**"
        #      )
        #      # FORCE CACHE UPDATE
        #     # self.log_channel = message.chat.id
        # #     logger.info(f"Health Check successful. Session validated: {message.chat.title}")

        # # 7.. Safe Peer Resolution
        # # We try to get_chat. If it fails, we rely on the manual /health command 
        # # to "Wake up" the caching layer later.
        # try:
        #     logger.info(f"�� Probing Channel {self.log_channel}...")
        #     chat = await self.app.get_chat(self.log_channel)
        #     logger.info(f"✅ Connection Established: {chat.title}")
            
        #     # Send Startup Signal
        #     await self.app.send_message(
        #         self.log_channel, 
        #         f"🔄 **Worker Restarted**\nready as: {self.worker_id}"
        #     )
        # except Exception as e:
        #     logger.warning(f"⚠️ Automatic Handshake failed: {e}")
        #     logger.warning("👉 ACTION: Send '/health' in the Log Channel/Group to fix cache!")


    async def task_watcher(self):
        """Watch Redis"""
        logger.info("Task Watcher started. Listening to 'queue:leech'...")
        while True:
            task_id = None
            try:
                task = await self.redis.brpop("queue:leech", timeout=30)
                if not task: continue
                if task:
                    payload = task[1]
                    logger.info(f"Consumed task: {payload}")
                    try:
                        # FORMAT: 0:task_id | 1:tmdb_id | 2:url | 3:type | 4:name | 5:user_id | 6:origin_chat_id | 7:user_tag | 8:trigger_msg_id
                        parts = payload.split("|")
                        if len(parts) < 9: 
                            logger.error("Malformed payload received."); continue   

                        task_id = parts[0]
                        tmdb_id = parts[1]
                        raw_url = parts[2]
                        type_hint = parts[3] if len(parts) > 3 else "auto"
                        name_hint = parts[4] if len(parts) > 4 else ""
                        user_id = parts[5] if len(parts) > 5 else "0"
                        origin_chat_id = parts[6] if len(parts) > 6 else settings.TG_LOG_CHANNEL_ID
                        # Capture user_tag (fallback to 0 if old payload)
                        user_tag = parts[7] if len(parts) > 7 else "0"
                        trigger_msg_id = parts[8] if len(parts) > 8 else None

                        # Update Status to 'Downloading'
                        status_key = f"task_status:{task_id}"

                        # 🛠️ DYNAMIC ENGINE DETECTION
                        raw_url = parts[2]
                        if raw_url.startswith("magnet") or ".torrent" in raw_url:
                            engine_name = "Aria2 v1.36.0"
                        else:
                            engine_name = "YT-DLP Native"

                        # ✅ REGISTER TASK IN GLOBAL UI
                        async with task_dict_lock:
                            task_dict[task_id] = {
                                "task_id": task_id,
                                "name": name_hint or f"TMDB {tmdb_id}",
                                "progress": 0,
                                "status": MirrorStatus.STATUS_QUEUED,
                                "user_tag": user_tag,
                                "engine": engine_name,
                                "processed": "0B",
                                "size": "0B",
                                "speed": "0B/s",
                                "eta": "Calculating...",
                                "origin_msg_id": trigger_msg_id # Stored for cleanup
                            }

                        # Update Status to 'Downloading' (Redis side)
                        await self.redis.hset(f"task_status:{task_id}", "status", "downloading")
                        try: 
                            # 1. Download
                            target_info = downloader.get_direct_url(raw_url)

                            if not target_info:
                                logger.error(f"❌ Could not resolve URL: {raw_url}")
                                # Cleanup registry on error
                                async with task_dict_lock: task_dict.pop(task_id, None)
                                continue # Skip to next task

                            local_path = await downloader.start_download(target_info, task_id=task_id)

                        except Exception as dl_err:
                            logger.error(f"Download Phase Failed: {dl_err}")
                            # ✅ CLEANUP ON DL FAIL
                            async with task_dict_lock: task_dict.pop(task_id, None)
                            continue
                        
                        if local_path and os.path.exists(local_path):
                            
                            # Optional: Rename before process
                            if name_hint:
                                dir_name = os.path.dirname(local_path)
                                ext = os.path.splitext(local_path)[1]
                                new_filename = f"{name_hint}{ext}"
                                new_path = os.path.join(dir_name, new_filename)
                                
                                logger.info(f"✏️ Renaming: {os.path.basename(local_path)} -> {new_filename}")
                                os.rename(local_path, new_path)
                                local_path = new_path
                                logger.info(f"Renamed hint applied: {new_filename}")

                            # 2. Upload with Hint
                            await self.leecher.upload_and_sync(
                                file_path=local_path, 
                                tmdb_id=int(tmdb_id),
                                type_hint=type_hint,
                                task_id=task_id,
                                user_id=user_id,
                                origin_chat_id=int(origin_chat_id),
                                trigger_msg_id=trigger_msg_id,
                                user_tag=user_tag
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

            finally:
                        # ✅ MASTER PURGE: Ensure task is REMOVED from UI no matter what happened
                        async with task_dict_lock:
                            if task_id in task_dict:
                                task_dict.pop(task_id, None)
                                logger.info(f"🧹 Registry cleaned for {task_id}")

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