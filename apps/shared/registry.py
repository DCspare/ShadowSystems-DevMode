# apps/shared/registry.py 
import asyncio

# The "Global Warehouse" for all active tasks
# Key: task_id | Value: Task object
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
    
    # --- Icons (MLTB Style) ---
    ICON_WAIT = "⏳"
    ICON_DL = "📥"
    ICON_UP = "📤"
    ICON_PROC = "⚙️"
    ICON_DONE = "✅"
    ICON_FAIL = "❌"