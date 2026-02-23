# apps/worker-video/handlers/mirror_leech_utils/download_utils/yt_dlp_download.py
import asyncio
import logging
import os
from re import search as re_search

import yt_dlp

from shared.settings import settings
from shared.status_utils.yt_dlp_status import YtDlpStatus

LOGGER = logging.getLogger("YtDlpDownload")


def sync_to_async(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args, **kwargs)


class YtDlpHelper:
    def __init__(self, listener):
        self._listener = listener
        self.status_obj = None
        self.opts = {
            "format": "bestvideo+bestaudio/best",
            "nocheckcertificate": True,
            "progress_hooks": [self._on_progress],
            "logger": self,  # Self-log to catch extension changes
            "quiet": True,
            "no_warnings": True,
            "cookiefile": settings.COOKIES_FILE_PATH,
            "restrictfilenames": True,
            "trim_file_name": 200,
            "socket_timeout": 10,
            "retries": 3,
            "fragment_retries": 3,
        }

    def debug(self, msg):
        # WZML-X Hack: Catch renaming during Merger
        if match := re_search(r".Merger..Merging formats into..(.*?).$", msg):
            newname = match.group(1).rsplit("/", 1)[-1]
            self._listener.name = newname

    def warning(self, msg):
        pass

    def error(self, msg):
        LOGGER.error(msg)

    def _on_progress(self, d):
        if self._listener.is_cancelled:
            raise Exception("TASK_CANCELLED_BY_USER")

        if d["status"] == "downloading":
            if self.status_obj:
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                self.status_obj.downloaded_bytes = downloaded
                self.status_obj.total_bytes = total
                self.status_obj.speed_raw = d.get("speed", 0)
                self.status_obj.eta_raw = d.get("eta", 0)

                # ✅ FIX: Call the listener so it can print the Terminal Heartbeat
                # We wrap it in a non-async call since _on_progress is sync
                self._listener.on_progress(downloaded, total)

    async def add_download(self, url, path, filename=None):
        self._gid = self._listener.task_id

        # 1. Initialize Status
        self.status_obj = YtDlpStatus(self._listener, self, self._gid)

        # 2. Setup Template
        self.opts["outtmpl"] = (
            os.path.join(path, filename) if filename else f"{path}/%(title)s.%(ext)s"
        )

        # 3. Notify Listener with the Object
        await self._listener.on_download_start(
            self.status_obj
        )  # ✅ Pass the status object

        # ✅ FIX: Actually LAUNCH the download in a background thread
        # This was missing! Without this, the worker just stops here.
        await sync_to_async(self._real_download, url)

    def _real_download(self, url):
        with yt_dlp.YoutubeDL(self.opts) as ydl:
            ydl.download([url])
