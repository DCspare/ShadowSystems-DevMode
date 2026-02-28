# apps/shared/status_utils/yt_dlp_status.py
from shared.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
)
from shared.progress import TaskProgress


class YtDlpStatus:
    def __init__(self, listener, obj, gid):
        self._listener = listener
        self._obj = obj  # This is the YoutubeDLHelper instance
        self._gid = gid
        self.engine = "YT-DLP Native"
        # Internal stats updated by engine hook
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed_raw = 0
        self.eta_raw = 0

        # ✅ Stats for Upload (via update_progress)
        self._tracker = None
        self._upload_status = None

    def update_progress(self, current_bytes, total_bytes, status=None):
        if not self._tracker:
            self._tracker = TaskProgress(total_bytes)

        self.downloaded_bytes = current_bytes
        self.total_bytes = total_bytes
        self._upload_status = status

        self.speed_raw = self._tracker.update(current_bytes)
        self.eta_raw = self._tracker.get_eta(current_bytes)

    def progress(self):
        if self.total_bytes > 0:
            pct = (self.downloaded_bytes / self.total_bytes) * 100
            return f"{pct:.2f}%"
        return "0%"

    def speed(self):
        return f"{get_readable_file_size(self.speed_raw)}/s"

    def processed_bytes(self):
        return get_readable_file_size(self.downloaded_bytes)

    def size(self):
        return get_readable_file_size(self.total_bytes)

    def eta(self):
        # ✅ FIX: Only call get_readable_time if eta_raw is actually a number
        if isinstance(self.eta_raw, int | float):
            return get_readable_time(self.eta_raw)
        return str(self.eta_raw)  # Return the string (usually "-") as is

    def status(self):
        """Unified status reporter handling Cancellation, Uploading, and Downloading."""
        if self._listener.is_cancelled:
            return MirrorStatus.STATUS_CANCELLED
        # Returns the specific status set during upload (if any),
        # otherwise defaults to Downloading
        return self._upload_status or MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        name = getattr(self._listener, "name", "Unknown")
        if callable(name):
            return name()
        return name

    def gid(self):
        return self._listener.task_id

    def get_ui_dict(self):
        """Returns a dictionary representation of the task for UI and logging."""
        return {
            "task_id": self.gid(),
            "name": self.name(),
            "status": self.status(),
            "progress": self.progress(),
            "processed": self.processed_bytes(),
            "size": self.size(),
            "speed": self.speed(),
            "eta": self.eta(),
            "user_tag": self._listener.user_tag,
            "engine": self.engine,
        }
