# apps/worker-video/handlers/status_manager.py
import asyncio
import logging
import time
from html import escape

from pyrogram.errors import FloodWait, MessageIdInvalid, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from shared.registry import task_dict, task_dict_lock
from shared.settings import settings
from shared.utils import ProgressManager, SystemMonitor

logger = logging.getLogger("StatusManager")


class StatusManager:
    def __init__(self, client):
        self.client = client
        self.status_msg = None  # Holds the ONE active status message
        self.last_update = 0
        self.is_running = False
        self.start_time = time.time()

    async def get_readable_message(self):
        """Builds the UI by polling polymorphic Status Objects."""
        async with task_dict_lock:
            # We filter for objects that actually have the status interface
            tasks = list(task_dict.values())

        if not tasks:
            return None, None

        msg = "<pre>🛰️ Shadow Systems Status</pre>\n"
        msg += f"<pre>📦 <b>Task Running:</b> {len(tasks)}/{settings.MAX_TOTAL_TASKS}</pre>\n"
        msg += "—" * 12 + "\n\n"

        for index, task in enumerate(tasks, start=1):
            # ✅ POLYMORPHIC CALLS: The object (Aria2Status/YtDlpStatus) handles its own math
            t_status = task.status()
            t_name = escape(str(task.name()))
            t_id = task.gid()
            progress_str = task.progress()  # e.g. "45.20%"
            user_tag = escape(str(task._listener.user_tag))
            engine = task.engine

            # Clean percentage for the bar
            try:
                pct = float(progress_str.strip("%"))
            except (
                ValueError,
                TypeError,
                AttributeError,
            ):  # ✅ FIX: Specific exceptions only
                pct = 0

            # Accurate Bar logic
            bar = ProgressManager.get_bar(pct)

            # Message Format
            msg += f"<b>{index}. {t_status}:</b>\n"
            msg += f"<code>{t_name}</code>\n"
            msg += f"{bar} {progress_str}\n"
            msg += f"<b>Processed:</b> {task.processed_bytes()} of {task.size()}\n"
            msg += f"<b>Speed:</b> {task.speed()}\n"
            msg += f"<b>ETA:</b> {task.eta()}\n"
            msg += f"<b>Engine:</b> <code>{engine}</code>\n"
            msg += f"👤 {user_tag}\n"
            msg += f"🆔 <code>{t_id}</code>\n"
            msg += f"🛑 /cancel_{t_id}\n\n"

        # Footer including System Health
        stats = SystemMonitor.get_stats()
        msg += "—" * 12 + "\n"
        msg += f"💻 <b>CPU:</b> {stats['cpu']}%\n"
        msg += f"🧠 <b>RAM:</b> {stats['mem']}%\n"
        msg += f"💾 <b>FREE:</b> {stats['free']}\n"
        uptime_sec = int(time.time() - self.start_time)
        msg += f"⏱️ <b>UPTIME:</b> {ProgressManager.get_readable_time(uptime_sec)}"

        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("♻️ Refresh Status", callback_data="check_status")]]
        )

        return msg, buttons

    async def delete_status(self):
        """Official MLTB Cleanup: Removes the message from Telegram."""
        if self.status_msg:
            try:
                await self.status_msg.delete()
            except:
                pass
            self.status_msg = None

    async def update_heartbeat(self):
        """The 6-second Background Loop (Heartbeat)"""
        self.is_running = True
        logger.info("💓 Status Heartbeat started.")
        while self.is_running:
            try:
                # Use a lock and create a snapshot to prevent 'dict changed size' errors
                async with task_dict_lock:
                    count = len(task_dict)
                    # This uses the new ShadowTask helper to get the UI-friendly dictionary
                    [
                        task.get_ui_dict()
                        for task in task_dict.values()
                        if hasattr(task, "get_ui_dict")
                    ]

                # CASE 1: No active tasks -> Delete message
                if count == 0:
                    if self.status_msg:
                        await self.delete_status()
                        logger.info("🗑️ Status message deleted (Queue Empty).")

                # CASE 2: Tasks active -> Send or Edit
                else:
                    (
                        msg_text,
                        buttons,
                    ) = (
                        await self.get_readable_message()
                    )  # This uses the snapshot logic now
                    if msg_text:
                        if not self.status_msg:
                            self.status_msg = await self.client.send_message(
                                chat_id=settings.TG_LOG_CHANNEL_ID,
                                text=msg_text,
                                reply_markup=buttons,
                            )
                        else:
                            # Throttled Edit to avoid flood
                            await self.status_msg.edit_text(
                                msg_text, reply_markup=buttons
                            )

            except FloodWait as f:
                logger.warning(f"⚠️ FloodWait: Sleeping for {f.value}s")
                await asyncio.sleep(f.value)
            except MessageNotModified:
                pass
            except MessageIdInvalid:
                # Allows a new UI message to spawn if original gets deleted by Admin
                self.status_msg = None
            except Exception as e:
                logger.error(f"Heartbeat CRASH: {e}", exc_info=True)
                # Optional: To prevent spamming, you could add a sleep here
                await asyncio.sleep(30)

            await asyncio.sleep(settings.STATUS_UPDATE_INTERVAL)
