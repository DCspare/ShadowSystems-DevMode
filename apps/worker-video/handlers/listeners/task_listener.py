# apps/worker-video/handlers/listeners/task_listener.py
import logging
from html import escape

from shared.registry import task_dict, task_dict_lock
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

        # --- State ---
        self.name = self.name_hint or f"TMDB {tmdb_id}"
        self.size = 0
        self.is_cancelled = False
        self.aria2_instance = None  # To be injected by DownloadManager
        self.local_path = None
        self.status_obj = None  # Will hold Aria2Status or YtDlpStatus
        self._last_term_pct = -1

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
        logger.info(f"✅ Download Phase Finished: {self.task_id}")
        # Note: Handover to flow_ingest happens in worker.py

    async def on_error(self, error_message):
        """Cleanup and Notify on failure."""
        async with task_dict_lock:
            if self.task_id in task_dict:
                task_dict.pop(self.task_id, None)

        logger.error(f"❌ Task Error [{self.task_id}]: {error_message}")

        # Notify user (Your notification feature)
        app = await TgClient.get_client()
        try:
            await app.send_message(
                chat_id=self.origin_chat_id,
                text=(
                    f"❌ <b>Task Failed for {self.user_tag}</b>\n\n"
                    f"🆔 ID: <code>{self.task_id}</code>\n"
                    f"⚠️ Error: <code>{escape(str(error_message))[:200]}</code>"
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to send error msg: {e}")

    async def clean_registry(self):
        """Final cleanup after successful upload."""
        async with task_dict_lock:
            task_dict.pop(self.task_id, None)
