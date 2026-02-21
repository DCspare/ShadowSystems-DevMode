# apps/worker-video/handlers/engines/aria2_engine.py
import os
import asyncio
import logging
import aria2p
from shared.settings import settings
from shared.registry import MirrorStatus

logger = logging.getLogger("Aria2Engine")

class Aria2Engine:
    def __init__(self, listener, redis):
        self.listener = listener
        self.redis = redis
        self.task_id = listener.task_id
        self.api = aria2p.API(
            aria2p.Client(host="http://localhost", port=6800, secret="")
        )

    async def download(self, url):
        try:
            options = {
                'dir': settings.DOWNLOAD_DIR,
                'seed-time': '0'
            }
            download = self.api.add_uris([url], options=options)
            gid = download.gid
            logger.info(f"🧲 Aria2 Tracking GID: {gid}")

            while True:
                # 1. Kill Switch Check (Redis)
                if await self.redis.get(f"kill_signal:{self.task_id}"):
                    self.api.remove([gid], force=True, clean=True)
                    raise Exception("TASK_CANCELLED_BY_USER")

                download = self.api.get_download(gid)
                
                # 2. Metadata Handover
                if download.followed_by:
                    new_item = download.followed_by[0]
                    gid = new_item.gid if not isinstance(new_item, str) else new_item
                    self.listener.on_progress(0, 0, status="🛰️ Fetching Metadata...")
                    continue

                if download.is_complete:
                    break

                if download.status == 'error':
                    raise Exception(download.error_message or "Aria2 unknown error")

                # 3. Progress Update
                if download.total_length > 0:
                    self.listener.on_progress(
                        download.completed_length,
                        download.total_length,
                        status=MirrorStatus.STATUS_DOWNLOADING
                    )
                
                await asyncio.sleep(2)

            # Finalize
            download = self.api.get_download(gid)
            largest_file = max(download.files, key=lambda f: f.length).path

            # Cleanup GID from Aria2 Memory
            self.api.remove([gid], force=True, clean=True)
            return str(largest_file)
        except Exception as e:
            await self.listener.on_error(str(e))
            raise e