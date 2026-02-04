# apps/worker-video/handlers/status_manager.py 
import time
import asyncio
import logging
from html import escape
from pyrogram.errors import FloodWait, MessageNotModified, MessageIdInvalid
from shared.registry import task_dict, task_dict_lock, MirrorStatus
from shared.utils import ProgressManager, SystemMonitor
from shared.settings import settings
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger("StatusManager")

class StatusManager:
    def __init__(self, client):
        self.client = client
        self.status_msg = None  # Holds the ONE active status message
        self.last_update = 0
        self.is_running = False

    async def get_readable_message(self):
        """Builds the MLTB-Style UI text."""
        async with task_dict_lock:
            tasks = list(task_dict.values())
        
        if not tasks:
            return None, None

        msg = f"🛰️ **Shadow Systems Status**\n"
        msg += f"<code>📦 **Task Running:** {len(tasks)}/{settings.MAX_TOTAL_TASKS}</code>\n"
        msg += "—" * 12 + "\n\n"

        for index, task in enumerate(tasks, start=1):
            t_status = task.get('status', 'Queued')
            t_name = escape(task.get('name', 'Unknown')) # Security: Escape HTML
            t_id = task.get('task_id')
            pct = task.get('progress', 0)
            user_tag = task.get('user_tag', 'User') # New
            engine = task.get('engine', 'Shadow-V2') # New
            
            # Accurate Bar logic
            bar = ProgressManager.get_bar(pct)
            
            # Message Format
            msg += f"**{index}. {t_status}:**\n"
            msg += f"<code>{t_name}</code>\n"
            msg += f"{bar} {pct}%\n"
            msg += f"**Processed:** {task.get('processed', '0B')} of {task.get('size', '0B')}\n"
            msg += f"**Speed:** {task.get('speed', '0B/s')}\n"
            msg += f"**ETA:** {task.get('eta', '0s')}\n"
            msg += f"**Engine:** `{engine}`\n" 
            msg += f"👤 {user_tag}\n"         
            msg += f"🆔 `{t_id}`\n"
            msg += f"🛑 /cancel_{t_id}\n\n"

        # Footer including System Health
        stats = SystemMonitor.get_stats()
        msg += "—" * 12 + "\n"
        msg += f"💻 **CPU:** {stats['cpu']}%\n"
        msg += f"🧠 **RAM:** {stats['mem']}%\n"
        msg += f"💾 **FREE:** {stats['free']}\n"
        msg += f"⏱️ **UPTIME:** {ProgressManager.get_readable_time(int(time.time() - self.client.start_time))}"

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("♻️ Refresh Status", callback_data="check_status")]
        ])

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
                    tasks_snapshot = list(task_dict.values())

                # CASE 1: No active tasks -> Delete message
                if count == 0:
                    if self.status_msg:
                        await self.delete_status()
                        logger.info("🗑️ Status message deleted (Queue Empty).")

                # CASE 2: Tasks active -> Send or Edit
                else:
                    msg_text, buttons = await self.get_readable_message() # This uses the snapshot logic now
                    if msg_text:
                        if not self.status_msg:
                            self.status_msg = await self.client.send_message(
                                chat_id=settings.TG_LOG_CHANNEL_ID,
                                text=msg_text,
                                reply_markup=buttons
                            )
                        else:
                            # Throttled Edit to avoid flood
                            await self.status_msg.edit_text(msg_text, reply_markup=buttons)
            
            except FloodWait as f:
                logger.warning(f"⚠️ FloodWait: Sleeping for {f.value}s")
                await asyncio.sleep(f.value)
            except (MessageNotModified, MessageIdInvalid):
                pass

            except Exception as e:
                if "MESSAGE_NOT_MODIFIED" not in str(e):
                    logger.debug(f"Heartbeat Error: {e}")
                if "MESSAGE_ID_INVALID" in str(e):
                    self.status_msg = None # Reset if deleted
            
            await asyncio.sleep(settings.STATUS_UPDATE_INTERVAL)