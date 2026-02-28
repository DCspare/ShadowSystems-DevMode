# apps/shared/registry.py
import asyncio

# The "Global Warehouse" for active Status Objects (Aria2Status, YtDlpStatus, etc.)
task_dict = {}
task_dict_lock = asyncio.Lock()

# WZML-X Style Queuing
queued_dl = {}  # {task_id: asyncio.Event}
queued_up = {}  # {task_id: asyncio.Event}
non_queued_dl = set()
non_queued_up = set()
queue_dict_lock = asyncio.Lock()


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


async def get_active_tasks_count():
    """Counts how many tasks are currently Downloading or Uploading."""

    async with task_dict_lock:
        return len(
            [
                t
                for t in task_dict.values()
                if t.status()
                not in [
                    MirrorStatus.STATUS_QUEUEDL,
                    MirrorStatus.STATUS_FAILED,
                    MirrorStatus.STATUS_COMPLETED,
                ]
            ]
        )
