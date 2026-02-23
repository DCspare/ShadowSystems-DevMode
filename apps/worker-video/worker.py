# apps/worker-video/worker.py
import asyncio
import logging
import os
import shutil
import signal
import subprocess
import sys
import time

sys.path.append("/app/shared")
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from handlers.download_manager import DownloadManager
from handlers.flow_ingest import MediaLeecher
from handlers.listeners.task_listener import TaskListener
from handlers.status_manager import StatusManager
from shared.database import db_service
from shared.registry import MirrorStatus, task_dict, task_dict_lock
from shared.settings import settings
from shared.tg_client import TgClient

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

        logger.info(
            f"🆔 Node Initialized | Mode: {self.mode} | Session: {self.session_name}"
        )

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
                "--file-allocation=none",  # Stop pre-allocating disk space (Fixes Docker Error)
                "--disk-cache=0",  # Disable RAM caching (Prevent buffer lag)
                "--max-connection-per-server=4",  # Keep connections low to avoid Google/Host blocks
                "--min-split-size=10M",
                "--dht-listen-port=6881",
                "--listen-port=6881",
                "--bt-enable-lpd=true",  # Local Peer Discovery
                "--enable-dht=true",
                "--user-agent=Transmission/3.00",  # Sometimes masks bot traffic
                "--quiet",
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
        await db_service.connect()  # Ensure kernel DB is connected for Shared Registry
        mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
        self.db = mongo_client["shadow_systems"]
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

        # 1. Start Primary Identity (1st Priority)
        started = await TgClient.start_bot(
            name=self.session_name, token_override=settings.TG_WORKER_BOT_TOKEN
        )

        # 2. Try User (Fallback start_user)
        await TgClient.start_user()  # For high-speed user transfers

        if not started and not TgClient.user:
            logger.critical("❌ No valid identity found (Bot or User). Exiting.")
            sys.exit(1)

        await TgClient.start_helpers()  # Spin up the HELPER_TOKENS

        # 3. Dynamic Handler Assignment
        # If in BOT mode, we use the Bot. If USER mode, and it worked, use User.
        self.app = await TgClient.get_client()
        self.leecher = MediaLeecher(self.app, self.db, self.redis)

        # 4. Handshake Pulse
        await TgClient.send_startup_pulse(
            f"WORKER-{self.session_name.upper()}"
        )  # 🛰️ Visible Handshake check

        await asyncio.sleep(2)

        # 5. Start Status Manager Heartbeat
        self.status_mgr = StatusManager(self.app)
        asyncio.create_task(self.status_mgr.update_heartbeat())  # Background Loop

    async def stop_services(self):
        """🛑 GRACEFUL SHUTDOWN ROUTINE"""
        if not self.is_running:
            return

        logger.info("🛑 Shutdown Signal Received. Cleaning up...")
        self.is_running = False

        # 1. Kill Aria2
        if hasattr(self, "aria2_proc"):
            try:
                self.aria2_proc.terminate()
                self.aria2_proc.wait(timeout=5)
            except Exception:
                self.aria2_proc.kill()

        # 2. Stop Pyrogram (THIS SAVES THE HANDSHAKE)
        try:
            logger.info("⏳ Saving Pyrogram Session (merging journal)...")
            await TgClient.stop()
            logger.info("✅ Pyrogram Session Saved & Closed.")
        except Exception as e:
            logger.error(f"Error during TgClient shutdown: {e}")

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
                task = await self.redis.brpop("queue:leech", timeout=1)
                if not task:
                    continue  # This allows the loop to check 'is_running' every 1 second

                if task:
                    payload = task[1]
                    logger.info(f"Consumed task: {payload}")
                    try:
                        # FORMAT: 0:task_id | 1:tmdb_id | 2:url | 3:type | 4:name | 5:user_id | 6:origin_chat_id | 7:user_tag | 8:trigger_msg_id
                        parts = payload.split("|")
                        if len(parts) < 9:
                            logger.error("Malformed payload received.")
                            continue

                        task_id = parts[0]
                        tmdb_id = parts[1]
                        raw_url = parts[2]
                        type_hint = parts[3] if len(parts) > 3 else "auto"
                        name_hint = parts[4] if len(parts) > 4 else ""
                        user_id = parts[5] if len(parts) > 5 else "0"
                        origin_chat_id = (
                            parts[6] if len(parts) > 6 else settings.TG_LOG_CHANNEL_ID
                        )
                        # Capture user_tag (fallback to 0 if old payload)
                        user_tag = parts[7] if len(parts) > 7 else "0"
                        trigger_msg_id = parts[8] if len(parts) > 8 else None

                        # 1. Initialize the professional TaskListener
                        listener = TaskListener(
                            task_id=task_id,
                            url=raw_url,
                            tmdb_id=tmdb_id,
                            user_id=user_id,
                            user_tag=user_tag,
                            origin_chat_id=int(origin_chat_id),
                            trigger_msg_id=trigger_msg_id,
                            type_hint=type_hint,
                            name_hint=name_hint,
                        )

                        # 2. Hand over to the Dispatcher
                        try:
                            # 2. Launch Download
                            manager = DownloadManager(self.redis)
                            # We wrap this in a task so we can monitor it
                            download_task = asyncio.create_task(manager.start(listener))

                            # 3. Robust Monitor Loop
                            while not download_task.done():
                                # ✅ FIX: Check Redis Kill Signal inside the wait loop
                                if await self.redis.get(f"kill_signal:{task_id}"):
                                    listener.is_cancelled = True
                                    logger.warning(
                                        f"🛑 Kill signal detected for {task_id}"
                                    )
                                    break

                                # Safety: If object is manually popped from registry
                                if task_id not in task_dict:
                                    break

                                await asyncio.sleep(2)

                        except Exception as dl_err:
                            logger.error(f"Download Phase Failed: {dl_err}")
                            # ✅ Ensure registry is cleaned on immediate start failure
                            async with task_dict_lock:
                                task_dict.pop(task_id, None)
                            continue

                        # 3. Process Downloaded File
                        # Resolve the actual path from the engine's result
                        local_path = None
                        for f in os.listdir(settings.DOWNLOAD_DIR):
                            # Fuzzy match based on task_id or name_hint
                            if task_id in f or (name_hint and name_hint in f):
                                local_path = os.path.join(settings.DOWNLOAD_DIR, f)
                                break

                        if local_path and os.path.exists(local_path):
                            await listener.on_download_complete()

                            # 4. Upload with Hint
                            await self.leecher.upload_and_sync(
                                file_path=local_path,
                                tmdb_id=int(tmdb_id),
                                type_hint=type_hint,
                                task_id=task_id,
                                user_id=user_id,
                                origin_chat_id=int(origin_chat_id),
                                trigger_msg_id=trigger_msg_id,
                                user_tag=user_tag,
                            )

                            # 3. Clean
                            if os.path.isfile(local_path):
                                os.remove(local_path)
                            logger.info(f"🗑️ Cleaned up: {local_path}")
                        else:
                            logger.error("Download ghosted.")

                    except Exception as task_err:
                        logger.error(f"❌ Task {task_id} Failed: {task_err}")

                        # 🛠️ SYSTEMATIC FAILURE CLEANUP
                        if self.redis:
                            # 1. Update status to Failed in Redis
                            await self.redis.hset(
                                f"task_status:{task_id}", "status", "failed"
                            )
                            # 2. Force expire the status so it clears from /status later
                            await self.redis.expire(f"task_status:{task_id}", 300)
                            # 3. IMPORTANT: Release the User's slot so they aren't blocked!
                            if user_id != "0":
                                limit_key = f"active_user_tasks:{user_id}"
                                await self.redis.srem(limit_key, task_id)
                                logger.info(f"🔓 Emergency Slot Release for {user_tag}")

                        # ✅ Send a notification to the user about the failure
                        try:
                            error_message = (
                                str(task_err).replace("<", "").replace(">", "")
                            )  # Sanitize
                            await self.app.send_message(
                                chat_id=int(origin_chat_id),
                                text=(
                                    f"❌ <b>Task Failed for {user_tag}</b>\n\n"
                                    f"<b>Task ID:</b> <code>{task_id}</code>\n"
                                    f"<b>Reason:</b> <pre>{error_message[:250]}</pre>\n\n"
                                    f"The queue has been cleared and your slot has been released."
                                ),
                            )
                        except Exception as notify_err:
                            logger.error(
                                f"Failed to send failure notification: {notify_err}"
                            )

                        await asyncio.sleep(2)
                        continue  # Move to the next task in queue

            except asyncio.CancelledError:
                # 🛠️ CRITICAL: Don't catch this as an "error". Raise it to exit the loop.
                raise
            except Exception as e:
                # Catch actual errors (Redis timeout, malformed data, etc)
                logger.error(f"Watcher Loop Error: {e}")
                await asyncio.sleep(2)

            finally:
                # ✅ FIX: Enhanced Master Purge
                # Try to get task_id from parts if it exists, otherwise use local var
                actual_id = None
                if task_id:
                    actual_id = task_id
                elif "parts" in locals() and len(parts) > 0:
                    actual_id = parts[0]

                if actual_id:
                    async with task_dict_lock:
                        if actual_id in task_dict:
                            task_dict.pop(actual_id, None)
                            logger.info(f"🧹 Registry cleaned for {actual_id}")

                # Reset current task payload for graceful shutdown re-queuing
                self.current_task_payload = None


async def main():
    worker = VideoWorker()

    # 🟢 SETUP SIGNAL HANDLERS
    loop = asyncio.get_running_loop()

    # Define what happens when Docker sends SIGTERM
    def handle_stop():
        # Using a sync threadsafe call to ensure event loop wakes up
        loop.call_soon_threadsafe(worker.shutdown_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_stop)

    try:
        await worker.init_services()

        # Run watcher and wait for shutdown signal
        watcher_task = asyncio.create_task(worker.task_watcher())

        # Wait here until signal is received
        await worker.shutdown_event.wait()
        logger.warning("🏁 Shutdown sequence initiated...")

        # # Signal received, wait for watcher to finish current cycle if needed
        # # (Optional: cancel watcher if you want instant kill)
        # watcher_task.cancel()

    except Exception as e:
        logger.error(f"Fatal Startup Error: {e}")
    finally:
        # 🛠️ SYSTEMATIC TEARDOWN
        logger.info("📦 Beginning Systematic Teardown...")

        # A. Stop Watcher
        if "watcher_task" in locals():
            watcher_task.cancel()
            try:
                await asyncio.wait_for(watcher_task, timeout=5)
            # ✅ FIX: Use asyncio.TimeoutError and ensure CancelledError is caught
            except (TimeoutError, asyncio.CancelledError):
                pass

        # B. Run the shutdown routine (SQLite save)
        await worker.stop_services()

        # C. Flush all logs and end
        logger.info("💀 Shadow Worker Offline.")
        # Ensure we exit even if background loops are hung
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
