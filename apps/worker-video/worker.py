# apps/worker-video/worker.py 
import os
import sys
import time
import asyncio
import signal
import logging
import subprocess
sys.path.append("/app/shared")
from redis.asyncio import Redis
from shared.tg_client import TgClient
from shared.database import db_service
from pyrogram.handlers import MessageHandler
from shared.settings import settings
from pyrogram import Client, filters
from handlers.downloader import downloader
from handlers.flow_ingest import MediaLeecher
from motor.motor_asyncio import AsyncIOMotorClient
from shared.registry import task_dict, task_dict_lock, MirrorStatus
from handlers.status_manager import StatusManager

TgClient.setup_logging()
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
        self.is_running = True
        self.shutdown_event = asyncio.Event()

        # 🔑 DYNAMIC SESSION NAME
        # Defaults to 'worker_video_default' if SESSION_FILE is missing in .env
        self.session_name = os.getenv("SESSION_FILE", "worker_video_default")
        self.mode = os.getenv("WORKER_MODE", "BOT").upper()
        
        logger.info(f"🆔 Node Initialized | Mode: {self.mode} | Session: {self.session_name}")

        try:
            self.log_channel = int(settings.TG_LOG_CHANNEL_ID)
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
        await db_service.connect() # Ensure kernel DB is connected for Shared Registry
        mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = mongo_client["shadow_systems"]
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # Initialize Downloader with THE BRIDGE
        self.start_aria2_daemon()
        await downloader.initialize(
            redis=self.redis
        )

        # 1. Start Primary Identity (1st Priority)
        started = await TgClient.start_bot(
            name=self.session_name, 
            token_override=settings.TG_WORKER_BOT_TOKEN
        )

        # 2. Try User (Fallback start_user)
        await TgClient.start_user()     # For high-speed user transfers

        if not started and not TgClient.user:
            logger.critical("❌ No valid identity found (Bot or User). Exiting.")
            sys.exit(1)

        await TgClient.start_helpers()  # Spin up the HELPER_TOKENS

        # 3. Dynamic Handler Assignment
        # If in BOT mode, we use the Bot. If USER mode, and it worked, use User.
        self.app = await TgClient.get_client()
        self.leecher = MediaLeecher(self.app, self.db, self.redis)

        # 4. Handshake Pulse
        await TgClient.send_startup_pulse(f"WORKER-{self.session_name.upper()}") # 🛰️ Visible Handshake check

        # 5. Start Status Manager Heartbeat
        self.status_mgr = StatusManager(self.app)
        asyncio.create_task(self.status_mgr.update_heartbeat()) # Background Loop
        
    async def stop_services(self):
        """🛑 GRACEFUL SHUTDOWN ROUTINE"""
        logger.info("🛑 Shutdown Signal Received. Cleaning up...")
        self.is_running = False
        
        # 1. Kill Aria2
        if hasattr(self, 'aria2_proc'):
            self.aria2_proc.terminate()
        
        # 2. Stop Pyrogram (CRITICAL: This saves the SQLite Session)
        await TgClient.stop()
        logger.info("✅ Pyrogram Session Saved & Closed.")

    async def task_watcher(self):
        """Watch Redis"""
        logger.info("Task Watcher started. Listening to 'queue:leech'...")
        while self.is_running:
            # 1. DEFENSIVE INITIALIZATION (Fixes UnboundLocalError)
            task_id = None
            tmdb_id = None
            user_id = "0"
            origin_chat_id = settings.TG_LOG_CHANNEL_ID
            trigger_msg_id = None
            user_tag = "User"
            try:
                task = await self.redis.brpop("queue:leech", timeout=10)
                if not task: continue

                payload = task[1]
                logger.info(f"Consumed task: {payload}")
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

    # 🟢 SETUP SIGNAL HANDLERS
    loop = asyncio.get_running_loop()

    # Define what happens when Docker sends SIGTERM
    def handle_stop():
        asyncio.create_task(worker.stop_services())
        worker.shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_stop)

    try:
        await worker.init_services()

        # Run watcher and wait for shutdown signal
        watcher_task = asyncio.create_task(worker.task_watcher())

        # Wait here until signal is received
        await worker.shutdown_event.wait()

        # Signal received, wait for watcher to finish current cycle if needed
        # (Optional: cancel watcher if you want instant kill)
        watcher_task.cancel()

    except asyncio.CancelledError:
        pass
    finally:
        # Final safety net
        if worker.is_running:
            await worker.stop_services()

if __name__ == "__main__":
    asyncio.run(main())