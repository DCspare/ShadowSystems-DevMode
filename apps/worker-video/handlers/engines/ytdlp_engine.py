# apps/worker-video/handlers/engines/ytdlp_engine.py
import os
import sys
import asyncio
import yt_dlp
import logging
from shared.settings import settings
from shared.registry import MirrorStatus

logger = logging.getLogger("YtdlpEngine")

class YtdlpEngine:
    def __init__(self, listener):
        self.listener = listener
        self.download_path = settings.DOWNLOAD_DIR
        self.task_id = listener.task_id

    def _progress_hook(self, d):
        if d.get('status') == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0:
                self.listener.on_progress(downloaded, total, status=MirrorStatus.STATUS_DOWNLOADING)

    def _run_download(self, url, opts):
        """Synchronous YT-DLP execution."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def download(self, url, final_path=None):
        """The main entry point for the engine."""
        
        opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': final_path or f"{self.download_path}/%(title)s.%(ext)s",
            'nocheckcertificate': True,
            'progress_hooks': [self._progress_hook],
            'quiet': True,
            'no_warnings': True,
            'cookiefile': os.getenv("COOKIES_FILE_PATH", "/app/cookies.txt"),
            'trim_file_name': 200,
            'restrictfilenames': True
        }

        loop = asyncio.get_event_loop()
        try:
            # Execute in thread to keep the event loop free
            await loop.run_in_executor(None, self._run_download, url, opts)
            
            # Fallback fuzzy search if YT-DLP changed the extension (e.g. .mkv to .mp4)
            if final_path:
                base_name = os.path.basename(final_path).rsplit('.', 1)[0]
                for f in os.listdir(self.download_path):
                    if base_name in f:
                        return os.path.join(self.download_path, f)
            
            return final_path
        except Exception as e:
            await self.listener.on_error(str(e))
            raise e