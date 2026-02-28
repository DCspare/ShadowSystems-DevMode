# apps/worker-video/handlers/mirror_leech_utils/download_utils/yt_dlp_download.py
import asyncio
import logging
import os
from re import search as re_search

import yt_dlp

from shared.registry import (
    non_queued_dl,
    queue_dict_lock,
    queued_dl,
    task_dict,
    task_dict_lock,
)
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

                # Call the listener so it can print the Terminal Heartbeat
                # We wrap it in a non-async call since _on_progress is sync
                self._listener.on_progress(downloaded, total)

        # Optional: Catch final filename if yt-dlp renames it after merging
        elif d["status"] == "finished":
            if "filename" in d:
                self._listener.name = d["filename"].rsplit("/", 1)[-1]

    async def add_download(self, url, path, filename=None):
        self._gid = self._listener.task_id

        # 0. Fetch the Brand Tag from settings
        # Example: "[ShadowSystem]"
        tag = settings.FILE_BRANDING_TAG if settings.FILE_BRANDING_TAG else ""

        # 1. Initialize Status
        self.status_obj = YtDlpStatus(self._listener, self, self._gid)

        # 2. Setup Template with Branding + Task ID
        if filename:
            # If a custom name is provided: "[ShadowSystem] MyMovie.mp4"
            final_name = f"{tag} {filename}".strip()
            self.opts["outtmpl"] = os.path.join(path, final_name)
            self._listener.name = final_name
        else:
            # Standard auto-name: "[ShadowSystem] Title.ID.extension"
            # We use a space after the tag for cleanliness
            template = f"{tag} %(title)s.{self._gid}.%(ext)s".strip()
            self.opts["outtmpl"] = os.path.join(path, template)
            # Placeholder name until yt-dlp fetches the real title
            self._listener.name = f"{tag} Fetching Title...".strip()

        # 3. Notify Listener that download is starting
        await self._listener.on_download_start(self.status_obj)

        # 4. Run the download
        # This blocks this specific task (but not the whole worker) until finished
        await sync_to_async(self._real_download, url)

        # WZML-X Update: Capture the actual filename after download finishes
        files = os.listdir(path)
        if files:
            # The first file that isn't a .part or .ytdl
            actual_file = next(
                (f for f in files if not f.endswith((".part", ".ytdl"))), files[0]
            )
            self._listener.name = actual_file

        # 5. Signal completion so worker.py moves to Uploading
        await self._listener.on_download_complete()

    def _real_download(self, url):
        try:
            with yt_dlp.YoutubeDL(self.opts) as ydl:
                ydl.download([url])
        except Exception as e:
            if (
                "403" in str(e)
                or "404" in str(e)
                or "400" in str(e)
                or "Expired" in str(e)
            ):
                # This message will be caught by the worker.py 'except' block
                raise Exception(
                    "❌ Download Link Expired, Forbidden or Bad Request. You must re-leech with a new link."
                )
            raise e
