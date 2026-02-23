# apps/shared/registry.py
import asyncio

# The "Global Warehouse" for active Status Objects (Aria2Status, YtDlpStatus, etc.)
task_dict = {}
task_dict_lock = asyncio.Lock()

class MirrorStatus:
    STATUS_UPLOADING = "Uploading"
    STATUS_DOWNLOADING = "Downloading"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Paused"
    STATUS_ARCHIVING = "Archiving"
    STATUS_EXTRACTING = "Extracting"
    STATUS_SPLITTING = "Splitting"
    STATUS_CHECKING = "Checking"
    STATUS_SEEDING = "Seeding"
    STATUS_PROCESSING = "Processing"
    STATUS_FAILED = "Failed"
    STATUS_CANCELLED = "Cancelled"
    STATUS_COMPLETED = "Completed"
