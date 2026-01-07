import os
import time
import logging
import PTN
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

logger = logging.getLogger("Leecher")

class MediaLeecher:
    """
    Shadow Logic: Handles media parsing, high-visibility upload tracking, 
    and Atlas library linking.
    """
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.branding = os.getenv("FILE_BRANDING_TAG", "[ShadowSystem]")

    def sanitize_title(self, raw_name: str) -> str:
        info = PTN.parse(raw_name)
        title = info.get('title', 'Unknown')
        year = f" ({info.get('year')})" if info.get('year') else ""
        quality = f" {info.get('quality')}" if info.get('quality') else ""
        return f"{self.branding} {title}{year}{quality}"

    async def progress_meter(self, current, total, filename):
        """High-speed terminal progress tracker for Monorepo logs."""
        percentage = (current / total) * 100
        # Log every 10% interval to avoid IDE log lag
        if int(percentage) % 10 == 0:
            filled = int(percentage // 5)
            bar = "█" * filled + "-" * (20 - filled)
            logger.info(f"📊 Transferring {filename[:15]}... |{bar}| {percentage:.1f}%")

    async def upload_and_sync(self, file_path: str, tmdb_id: int):
        try:
            target_id = int(os.getenv("TG_LOG_CHANNEL_ID"))
            file_name = os.path.basename(file_path)
            clean_name = self.sanitize_title(file_name)
            
            logger.info(f"🚀 Launching Byte-Handshake for: {clean_name}")

            # 1. Telegram Ingestion
            sent_msg = await self.client.send_document(
                chat_id=target_id,
                document=file_path,
                file_name=f"{clean_name}{os.path.splitext(file_name)[1]}",
                caption=f"🎥 **{clean_name}**\n\n⚡ Verified MTProto Source.",
                force_document=True,
                progress=self.progress_meter,
                progress_args=(file_name,)
            )

            file_id = sent_msg.document.file_id
            
            # 2. Atlas Indexing
            file_data = {
                "quality": PTN.parse(file_name).get('quality', '720p'),
                "telegram_id": file_id,
                "size_bytes": os.path.getsize(file_path),
                "added_at": int(time.time())
            }

            await self.db.library.update_one(
                {"tmdb_id": int(tmdb_id)},
                {"$push": {"files": file_data}, "$set": {"status": "available"}}
            )
            
            logger.info(f"✅ PROTOCOL COMPLETE: {clean_name} successfully mapped to TMDB:{tmdb_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ingestion Aborted: {e}")
            return False
