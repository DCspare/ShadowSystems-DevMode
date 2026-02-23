# apps/worker-video/handlers/listener.py
import sys
import logging
from shared.registry import task_dict, task_dict_lock, ShadowTask, MirrorStatus

logger = logging.getLogger("TaskListener")

class TaskListener:
    """
    The Bridge between Engines and the Registry.
    One Listener instance is created per Task.
    """
    def __init__(self, task_id, name, user_tag, user_id, origin_chat_id):
        self.task_id = task_id
        self.name = name
        self.user_id = user_id
        self.origin_chat_id = origin_chat_id
        
        # Initialize the Task in the Global Registry
        self.task = ShadowTask(task_id, name, user_tag)
        self._last_term_pct = -1
        
    async def on_setup(self, engine_name="Shadow-V2"):
        """Registers the task in the global dictionary."""
        self.task.set_engine(engine_name)
        async with task_dict_lock:
            task_dict[self.task_id] = self.task
        logger.info(f"🆕 Task Registered: {self.task_id} | Engine: {engine_name}")

    def on_progress(self, current, total, status=None):
        """Called by engines to update UI."""
        self.task.update_progress(current, total, status)

        # Lightweight Terminal Heartbeat (Every 30%)
        # This works perfectly in Docker/Cloud logs
        pct = self.task.progress
        if pct % 30 == 0 and pct != self._last_term_pct:
            self._last_term_pct = pct
            ui = self.task.get_ui_dict()
            # Static print (no \r) ensures it shows up in Docker logs correctly
            logger.info(f"📊 [{ui['engine']}] {pct}% | {ui['speed']} | ETA: {ui['eta']} | ID: {self.task_id}")

    async def on_complete(self):
        """Called when engine finishes."""
        self.task.status = MirrorStatus.STATUS_COMPLETED
        sys.stdout.write(f"\n✅ Task Engine Finished: {self.task_id}\n")
        sys.stdout.flush()

    async def on_error(self, message):
        """Called when engine fails."""
        self.task.status = MirrorStatus.STATUS_FAILED
        logger.error(f"❌ Task Engine Error [{self.task_id}]: {message}")
        # Clean cleanup logic will be handled by the Manager