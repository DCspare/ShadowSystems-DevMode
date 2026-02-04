# apps/shared/registry.py 
import asyncio

# The "Global Warehouse" for all active tasks
# Key: task_id | Value: Task object
task_dict = {}
task_dict_lock = asyncio.Lock()

class MirrorStatus:
    STATUS_DOWNLOAD = "Download"
    STATUS_UPLOAD = "Upload"
    STATUS_QUEUED = "Queued"
    STATUS_CANCELLED = "Cancelled"
    STATUS_MIRRORING = "Mirroring"