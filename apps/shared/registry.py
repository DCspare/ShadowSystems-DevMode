# apps/shared/registry.py 
import asyncio
import time
from shared.progress import TaskProgress
from shared.utils import ProgressManager

# The Global Registry
task_dict = {}
task_dict_lock = asyncio.Lock()

class MirrorStatus:
    # --- States ---
    STATUS_QUEUED = "Queued"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_UPLOADING = "Uploading"
    STATUS_PROCESSING = "Processing" # For FFmpeg/Samples
    STATUS_EXTRACTING = "Extracting" # For Zips
    STATUS_CANCELLED = "Cancelled"
    STATUS_FAILED = "Failed"
    STATUS_COMPLETED = "Completed"

class ShadowTask:
    """
    The Unified Task Object.
    Every active download/upload is an instance of this class.
    """
    def __init__(self, task_id, name, user_tag, engine="Shadow-V2"):
        self.task_id = task_id
        self.name = name
        self.user_tag = user_tag
        self.engine = engine
        
        # State
        self.status = MirrorStatus.STATUS_QUEUED
        self.progress = 0
        self.processed_bytes = 0
        self.total_bytes = 0
        self.speed_raw = 0
        self.eta = "Calculating..."
        
        # Internal Tracker (Shared Logic)
        self._tracker = None

    def update_progress(self, current_bytes, total_bytes, status=None):
        """Standardized update method used by all engines."""
        if total_bytes <= 0: return
        
        if not self._tracker:
            self._tracker = TaskProgress(total_bytes)
            self.total_bytes = total_bytes

        self.processed_bytes = current_bytes
        self.status = status or self.status
        
        # Calculate Math via shared TaskProgress
        self.speed_raw = self._tracker.update(current_bytes)
        self.progress = int(current_bytes * 100 / total_bytes)
        self.eta = self._tracker.get_eta(current_bytes)

    def set_engine(self, engine_name: str):
        """Updates the engine name (e.g., from 'Shadow-V2' to 'Aria2')"""
        self.engine = engine_name
        
    def get_ui_dict(self):
        """Returns the dictionary format expected by the StatusManager."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "progress": self.progress,
            "processed": ProgressManager.get_readable_file_size(self.processed_bytes),
            "size": ProgressManager.get_readable_file_size(self.total_bytes),
            "speed": f"{ProgressManager.get_readable_file_size(self.speed_raw)}/s",
            "eta": self.eta,
            "user_tag": self.user_tag,
            "engine": self.engine
        }
