# apps/worker-video/handlers/listeners/task_listener.py
import logging
import os
import shutil
from html import escape

from shared.registry import MirrorStatus, task_dict, task_dict_lock
from shared.settings import settings
from shared.tg_client import TgClient

logger = logging.getLogger("TaskListener")


class TaskListener:
    """
    The Lifecycle Manager (Shadow-V2).
    Coordinates: Download -> Rename -> Process -> Upload -> Index.
    """

    def __init__(
        self,
        task_id,
        url,
        tmdb_id,
        user_id,
        user_tag,
        origin_chat_id,
        trigger_msg_id,
        type_hint="auto",
        name_hint="",
    ):
        # --- Metadata (Your existing features) ---
        self.task_id = task_id
        self.url = url
        self.tmdb_id = tmdb_id
        self.user_id = user_id
        self.user_tag = user_tag
        self.origin_chat_id = origin_chat_id
        self.trigger_msg_id = trigger_msg_id
        self.type_hint = type_hint
        self.name_hint = name_hint

        # WZML-X LOGIC: Unique directory per task
        self.dir = os.path.join(settings.DOWNLOAD_DIR, str(task_id))
        os.makedirs(self.dir, exist_ok=True)

        # --- State ---
        self.name = self.name_hint or f"TMDB {tmdb_id}"
        self.size = 0
        self.is_cancelled = False
        self.is_finished = False
        self.aria2_instance = None  # To be injected by DownloadManager
        self.local_path = None
        self.status_obj = None  # Will hold Aria2Status or YtDlpStatus
        self._last_term_pct = -1
        # Register in the global task_dict immediately so /status sees it
        task_dict[self.task_id] = self

        # Delete the unique task folder
        if os.path.exists(self.dir):
            shutil.rmtree(self.dir)
            logger.info(f"🧹 Cleaned task directory: {self.dir}")

    def status(self):
        if self.is_cancelled:
            return MirrorStatus.STATUS_CANCELLED
        if self.status_obj:
            return self.status_obj.status()
        return MirrorStatus.STATUS_QUEUEDL  # Default if engine hasn't started yet

    async def on_download_start(self, status_obj):
        """Registers the polymorphic status object in the registry."""
        self.status_obj = status_obj
        async with task_dict_lock:
            task_dict[self.task_id] = status_obj
        logger.info(f"🚀 Task Started: {self.task_id} | Engine: {status_obj.engine}")

    def on_progress(self, current, total, status=None):
        """Unified Terminal Heartbeat Logger."""
        if total > 0:
            pct = int(current * 100 / total)
            # Only log every 20% to prevent terminal spam
            if pct % 20 == 0 and pct != self._last_term_pct:
                self._last_term_pct = pct
                if self.status_obj:
                    # MLTB/WZML Style Terminal Output
                    print(
                        f"📊 [{self.status_obj.engine}] {pct}% | {self.status_obj.speed()} | ETA: {self.status_obj.eta()} | ID: {self.task_id}",
                        flush=True,
                    )

    async def on_download_complete(self):
        """Called when engine finishes. Transition to Upload."""
        self.is_finished = True
        logger.info(f"✅ Download Phase Finished: {self.task_id}")
        # Note: Handover to flow_ingest happens in worker.py

    async def on_error(self, error_message):
        """Cleanup and Notify on failure."""
        # 1. IMMEDIATE REGISTRY CLEANUP (Kills the stale status message)
        async with task_dict_lock:
            if self.task_id in task_dict:
                task_dict.pop(self.task_id, None)
                logger.info(f"🧹 Removed failed task {self.task_id} from registry.")

        logger.error(f"❌ Task Error [{self.task_id}]: {error_message}")

        # 2. PREPARE MESSAGE
        msg = (
            f"❌ <b>Task Failed</b>\n\n"
            f"👤 <b>User:</b> {self.user_tag}\n"
            f"🆔 <b>ID:</b> <code>{self.task_id}</code>\n"
            f"⚠️ Error: <code>{escape(str(error_message))[:200]}</code>"
        )

        app = await TgClient.get_client()

        try:
            # Attempt A: Send to the user/group where command started
            # We don't use reply_to_message_id here to avoid issues if the message was deleted
            await app.send_message(chat_id=self.origin_chat_id, text=msg)
            logger.info(f"🔔 Notified origin chat {self.origin_chat_id} about failure.")
        except Exception as e:
            # Attempt B: Fallback to Log Channel if Peer ID is invalid or user blocked bot
            logger.warning(
                f"⚠️ Could not notify origin {self.origin_chat_id} ({e}). Routing to Log Channel."
            )
            try:
                await app.send_message(
                    chat_id=settings.TG_LOG_CHANNEL_ID,
                    text=f"🚩 <b>Failed Notification Fallback:</b>\n\n{msg}",
                )
            except Exception as log_err:
                logger.error(f"❌ Total Notification Failure: {log_err}")

    async def clean_registry(self):
        """Final cleanup called after upload finishes."""
        async with task_dict_lock:
            if self.task_id in task_dict:
                task_dict.pop(self.task_id, None)

        # We leave the physical directory removal to the worker's 'finally' block
        # to ensure it happens even if the upload fails/crashes.
        pass
