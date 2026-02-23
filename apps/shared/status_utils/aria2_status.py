# apps/shared/status_utils/aria2_status.py
import logging

from shared.ext_utils.status_utils import (
    MirrorStatus,
)

LOGGER = logging.getLogger("Aria2Status")


class Aria2Status:
    def __init__(self, gid, listener, aria2_instance):
        self._gid = gid
        self._listener = listener
        self._aria2 = aria2_instance  # Passed from the engine
        self._info = None  # Holds the raw aria2 status object
        self.engine = "Aria2 v1.36.0"

    def update(self):
        """Syncs the internal info from Aria2 daemon."""
        try:
            self._info = self._aria2.get_download(self._gid)
            if self._info.followed_by:
                # Handle Metadata -> Torrent handover
                self._gid = self._info.followed_by[0].gid
                self._info = self._aria2.get_download(self._gid)
        except:
            pass

    def progress(self):
        self.update()
        return f"{self._info.progress:.2f}%" if self._info else "0%"

    def update_progress(self, current, total, status=None):
        """Standardized update call used during Upload phase."""
        # For Aria2, we only need this during upload because download
        # is handled by the internal .update() loop.
        if status == MirrorStatus.STATUS_UPLOADING:
            # Logic to override aria2 stats with upload stats
            # (Mirroring the YtDlpStatus logic above)
            pass

    def speed(self):
        return f"{self._info.download_speed_string()}/s" if self._info else "0B/s"

    def processed_bytes(self):
        return self._info.completed_length_string() if self._info else "0B"

    def size(self):
        return self._info.total_length_string() if self._info else "0B"

    def eta(self):
        return self._info.eta_string() if self._info else "∞"

    def status(self):
        if not self._info:
            return MirrorStatus.STATUS_QUEUEDL
        state = self._info.status
        if state == "active":
            return MirrorStatus.STATUS_DOWNLOADING
        if state == "waiting":
            return MirrorStatus.STATUS_QUEUEDL
        if state == "paused":
            return MirrorStatus.STATUS_PAUSED
        if state == "complete":
            return MirrorStatus.STATUS_COMPLETED
        if state == "error":
            return MirrorStatus.STATUS_FAILED
        return MirrorStatus.STATUS_DOWNLOADING

    def name(self):
        return self._listener.name

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
