# apps/worker-video/worker.py
import asyncio
import logging
import os
import random
import shutil
import signal
import subprocess
import sys
import time

from shared.ext_utils.button_build import ButtonMaker

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
        self.semaphore = asyncio.Semaphore(settings.MAX_TOTAL_TASKS)

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
        """🧹 WIPER: Removes all stale files from crash but ignores config/cookies"""
        dl_dir = settings.DOWNLOAD_DIR
        cookie_name = os.path.basename(settings.COOKIES_FILE_PATH)  # Get 'cookies.txt'

        logger.info(f"🧹 Cleaning slate at: {dl_dir}")
        if os.path.exists(dl_dir):
            try:
                # Remove all files in the directory
                for filename in os.listdir(dl_dir):
                    # 🛡️ EXCLUSION LOGIC
                    if filename == cookie_name:
                        continue

                    file_path = os.path.join(dl_dir, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                logger.info("✅ Downloads folder purged (Cookies preserved).")
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

        # Start Primary Identity (Added 'plugins' to load the recovery handler)
        plugins_config = dict(root="handlers")

        # 1. Start Primary Identity (1st Priority)
        started = await TgClient.start_bot(
            name=self.session_name,
            token_override=settings.TG_WORKER_BOT_TOKEN,
            plugins=plugins_config,
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

        # STARTUP RECOVERY
        await self.reconcile_incomplete_tasks()

        # 5. Start Status Manager Heartbeat
        self.status_mgr = StatusManager(self.app)
        asyncio.create_task(self.status_mgr.update_heartbeat())  # Background Loop

    async def reconcile_incomplete_tasks(self):
        """WZML-X Style: Checks MongoDB for tasks that never finished."""
        try:
            logger.info("🔍 Checking for incomplete tasks from previous session...")
            incompletes = await self.db.incomplete_tasks.find().to_list(length=100)

            if not incompletes:
                logger.info("✅ No incomplete tasks found.")
                return

            # Build WZML-X Recovery Menu
            buttons = ButtonMaker()
            buttons.data_button("♻️ Resume All", "resume_all_tasks")
            buttons.data_button("🗑️ Clear All", "clear_incomplete_tasks")
            buttons.data_button("🔍 Select Tasks", "select_incomplete_tasks")

            msg = (
                f"🚩 <b>Incomplete Tasks Detected!</b>\n"
                f"System found <code>{len(incompletes)}</code> tasks that were interrupted by a crash or restart.\n\n"
                f"<i>What would you like to do?</i>"
            )

            # ✅ FIX: Send to Log Channel instead of Owner DM to avoid PEER_ID_INVALID
            # Also added a try/except so a notification failure doesn't crash the worker
            try:
                await self.app.send_message(
                    chat_id=settings.TG_LOG_CHANNEL_ID,
                    text=msg,
                    reply_markup=buttons.build_menu(2),
                )
                logger.info("📢 Recovery notification sent to Log Channel.")
            except Exception as notify_err:
                logger.error(f"⚠️ Could not send recovery alert: {notify_err}")
                # We don't 'return' here because we still want the worker to function

        except Exception as e:
            logger.error(f"❌ Error during task reconciliation: {e}")

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

    async def process_task(self, payload):
        """The 'Worker Lane': This runs a single task from start to finish."""
        # 1. PRE-INITIALIZE (Solves UnboundLocalError forever)
        task_id = payload.split("|")[0]
        local_path = None
        user_id = "0"
        listener = None

        # A Semaphore is like a bouncer. Only 'MAX_TOTAL_TASKS' can pass this line at once.
        async with self.semaphore:
            try:
                # 2. RECORD IN MONGODB (The Safety Net)
                await self.db.incomplete_tasks.update_one(
                    {"_id": task_id},
                    {"$set": {"payload": payload, "added_at": time.time()}},
                    upsert=True,
                )

                # Use a limited split (8) to ensure that if the URL contains '|',
                # it doesn't break the rest of the indices.
                parts = payload.split("|", 8)

                # CLEANING: Strip hidden whitespace from every part to ensure .isdigit() works
                parts = [p.strip() for p in parts]

                # Ensure we have all 9 parts
                while len(parts) < 9:
                    parts.append("")
                (
                    task_id,
                    tmdb_id,
                    raw_url,
                    type_hint,
                    name_hint,
                    user_id,
                    origin_chat_id,
                    user_tag,
                    trigger_msg_id,
                ) = parts

                # LOG THE FULL PAYLOAD FOR DEBUGGING
                logger.info(
                    f"📥 Processing: ID={task_id} | TMDB={tmdb_id} | Name_Hint={name_hint} | User={user_tag}"
                )

                # Sanitize IDs: Convert to int only if it's a pure digit string
                tmdb_id = int(tmdb_id) if tmdb_id and tmdb_id.isdigit() else 0

                # origin_chat_id must handle the '-' sign for channel IDs
                origin_chat_id = (
                    int(origin_chat_id)
                    if origin_chat_id and origin_chat_id.replace("-", "").isdigit()
                    else settings.TG_LOG_CHANNEL_ID
                )

                # 3. Initialize Listener
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

                # 4. Launch Download Engine
                manager = DownloadManager(self.redis)
                await manager.start(listener)

                # 5. SMART WAIT: Wait for 'is_finished' flag or 'is_cancelled'
                while not listener.is_finished:
                    if listener.is_cancelled or await self.redis.get(
                        f"kill_signal:{task_id}"
                    ):
                        listener.is_cancelled = True
                        break
                    await asyncio.sleep(2)

                # 6. Upload Phase (If finished and not cancelled)
                if listener.is_finished and not listener.is_cancelled:
                    # Random jitter (0.1 to 1.5s) so they don't hit the DB/API at the exact same millisecond
                    await asyncio.sleep(random.uniform(0.1, 1.5))
                    logger.info(f"📤 Transitioning to Upload: {task_id}")

                    # Force a 1-second sleep to ensure files are flushed to disk
                    await asyncio.sleep(1)

                    # WZML-X LOGIC: The file is simply the first file in the listener.dir
                    files = os.listdir(listener.dir)
                    if not files:
                        raise Exception("Download directory is empty!")

                    # Get the full path of the downloaded file
                    local_path = os.path.join(listener.dir, files[0])

                    if local_path and os.path.exists(local_path):
                        # Update status to Uploading so users see it
                        if listener.status_obj:
                            listener.status_obj._upload_status = (
                                MirrorStatus.STATUS_UPLOADING
                            )

                        await self.leecher.upload_and_sync(
                            file_path=local_path,
                            tmdb_id=int(tmdb_id),
                            type_hint=type_hint,
                            task_id=task_id,
                            user_id=user_id,
                            origin_chat_id=int(origin_chat_id),
                            trigger_msg_id=trigger_msg_id,
                            user_tag=user_tag,
                            name_hint=name_hint,
                        )
                    else:
                        raise Exception("Downloaded file disappeared or name mismatch.")

                # 7. SUCCESS: DELETE FROM MONGODB
                await self.db.incomplete_tasks.delete_one({"_id": task_id})

            except Exception as e:
                logger.error(f"❌ Task {task_id} failed: {e}")
                # Clean MongoDB and Redis status on known failure
                await self.db.incomplete_tasks.delete_one({"_id": task_id})
                await self.redis.delete(f"task_status:{task_id}")

                # Notify user and CLEAR registry via the listener
                if listener:
                    await listener.on_error(str(e))

            finally:
                # 1. PHYSICAL CLEANUP (The Nuke)
                if listener and os.path.exists(listener.dir):
                    try:
                        shutil.rmtree(listener.dir, ignore_errors=True)
                    except:
                        pass

                # 2. MEMORY CLEANUP (The Double-Tap)
                # Even if listener.on_error failed, we pop the dict here
                async with task_dict_lock:
                    if task_id in task_dict:
                        task_dict.pop(task_id, None)

                # 3. REDIS SLOT RELEASE
                if user_id != "0":
                    await self.redis.srem(f"active_user_tasks:{user_id}", task_id)

                logger.info(f"🏁 Finalized cleanup for task: {task_id}")

    async def task_watcher(self):
        """The 'Ear': It pulls tasks from Redis and spawns them into parallel lanes."""
        logger.info(f"🚀 Parallel Worker Online. Max Slots: {settings.MAX_TOTAL_TASKS}")
        while self.is_running:
            try:
                task = await self.redis.brpop("queue:leech", timeout=1)
                if task:
                    payload = task[1]
                    # We 'create_task' so the loop doesn't wait (ASYNC PARALLEL)
                    asyncio.create_task(self.process_task(payload))
            except Exception as e:
                logger.error(f"Watcher Error: {e}")
                await asyncio.sleep(2)


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
            except (TimeoutError, asyncio.CancelledError):
                pass

        # B. Run the shutdown routine (SQLite save)
        await worker.stop_services()

        # C. Flush all logs and end
        logger.info("💤 Shadow Worker Offline.")
        # Ensure we exit even if background loops are hung
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
