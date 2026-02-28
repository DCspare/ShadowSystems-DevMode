# apps/worker-video/handlers/download_manager.py
import logging

import aria2p

from handlers.mirror_leech_utils.download_utils.aria2_download import add_aria2_download
from handlers.mirror_leech_utils.download_utils.direct_link_generator import (
    direct_link_generator,
)
from handlers.mirror_leech_utils.download_utils.yt_dlp_download import YtDlpHelper
from shared.settings import settings

logger = logging.getLogger("DownloadManager")


class DownloadManager:
    def __init__(self, redis):
        self.redis = redis
        # Re-use global aria2 instance for the engines
        self.aria2 = aria2p.API(
            aria2p.Client(host="http://localhost", port=6800, secret="")
        )

    async def start(self, listener):
        """Analyzes URL and dispatches to the correct WZML-style helper."""
        url = listener.url
        listener.aria2_instance = self.aria2  # Inject instance

        # 1. Bypass Check: Skip generator for YouTube and other streaming sites
        streaming_hosts = [
            "youtube.com",
            "youtu.be",
            "twitter.com",
            "x.com",
            "instagram.com",
            "tiktok.com",
        ]

        if not any(x in url for x in streaming_hosts):
            try:
                # Only try bypassing for file-hosting links
                url = direct_link_generator(url)
                if isinstance(url, tuple):
                    url = url[0]  # Handle (link, header) tuples
                logger.info(f"🔗 URL Bypassed: {listener.task_id}")
            except Exception as e:
                logger.info(f"ℹ️ Direct Link Generator skipped: {e}")

        # 2. Selection Logic
        is_torrent = url.startswith(("magnet:", "bc:")) or url.endswith(".torrent")

        if is_torrent:
            # Torrent -> Aria2
            return await add_aria2_download(listener, url, listener.dir)
        else:
            # Everything else -> YT-DLP (Handles direct files and sites)
            # WZML-X uses YT-DLP as a robust fallback for raw links too
            yt_helper = YtDlpHelper(listener)
            # Use name_hint if provided to force filename
            filename = f"{listener.name_hint}.mp4" if listener.name_hint else None
            return await yt_helper.add_download(url, listener.dir, filename)
