# apps/worker-video/handlers/download_manager.py (formaerly downloader.py)
import os, time, logging, yt_dlp
from shared.settings import settings
from handlers.engines.aria2_engine import Aria2Engine
from handlers.engines.ytdlp_engine import YtdlpEngine

logger = logging.getLogger("DownloadManager")

class DownloadManager:
    def __init__(self, redis):
        self.redis = redis

    def _get_safe_filename(self, candidate, default="video"):
        """Prevents Filename too long (Linux limit 255)"""
        if not candidate: return f"{default}_{int(time.time())}.mp4"
        clean = candidate.split("?")[0]
        if len(clean) > 200:
            ext = os.path.splitext(clean)[1] or ".mp4"
            return f"short_{int(time.time())}{ext}"
        return clean

    def probe_link(self, url: str) -> dict:
        """Analyzes URL to determine the best engine."""
        try:
            with yt_dlp.YoutubeDL({'format': 'best', 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get('direct'):
                    return {"url": url, "filename": self._get_safe_filename(os.path.basename(url)), "type": "direct"}
                
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                return {"url": info.get('url'), "filename": self._get_safe_filename(f"{title}.{ext}"), "type": "video_site"}
        except:
            return {"url": url, "filename": self._get_safe_filename(url.split("/")[-1]), "type": "raw"}

    async def start(self, url, task_id, listener):
        """Dispatches the task to the correct engine."""
        
        # 1. Probing
        target = self.probe_link(url)
        raw_link = target['url']

        # 2. Update Listener with chosen Engine Name before starting
        engine_name = "Aria2 v1.36.0" if (raw_link.startswith("magnet") or ".torrent" in raw_link) else "YT-DLP Native"
        await listener.on_setup(engine_name)
        
        # 3. Filename Prep
        fname = target['filename']
        final_path = os.path.join(settings.DOWNLOAD_DIR, fname)

        # 4. Dispatch
        if engine_name.startswith("Aria2"):
            engine = Aria2Engine(listener, self.redis)
            return await engine.download(raw_link)
        else:
            engine = YtdlpEngine(listener)
            return await engine.download(raw_link, final_path=final_path)

# Singleton instance
# Note: Redis will be injected by worker.py