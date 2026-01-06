import os
import time
import logging
import PTN
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

logger = logging.getLogger("Leecher")

class MediaLeecher:
    """
    Shadow Logic: Handles media processing and library sync.
    Includes auto-peer resolution for Supergroups.
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

    async def get_log_chat(self):
        """Resolves and caches the peer ID before operation"""
        try:
            target = int(os.getenv("TG_LOG_CHANNEL_ID"))
            # Pre-emptive resolution caches the ID in Pyrogram's memory
            chat = await self.client.get_chat(target)
            return chat.id
        except Exception as e:
            logger.warning(f"Initial peer resolve failed: {e}. Trying secondary method...")
            return int(os.getenv("TG_LOG_CHANNEL_ID"))

    async def upload_and_sync(self, file_path: str, tmdb_id: int):
        try:
            # 1. Resolve peer with self-healing
            log_channel = await self.get_log_chat()
            
            file_name = os.path.basename(file_path)
            clean_name = self.sanitize_title(file_name)
            
            logger.info(f"Uploading {file_name} to Log Storage...")
            
            # 2. Telegram Transfer
            # We send directly to the resolved chat ID
            sent_msg = await self.client.send_document(
                chat_id=log_channel,
                document=file_path,
                file_name=f"{clean_name}{os.path.splitext(file_name)[1]}",
                caption=f"🎥 **{clean_name}**\n\n⚡ Source Synchronized.",
                force_document=True
            )

            file_id = sent_msg.document.file_id
            
            # 3. Final Database Update
            file_data = {
                "quality": PTN.parse(file_name).get('quality', '720p'),
                "telegram_id": file_id,
                "added_at": int(time.time())
            }

            await self.db.library.update_one(
                {"tmdb_id": int(tmdb_id)},
                {"$push": {"files": file_data}, "$set": {"status": "available"}}
            )
            
            logger.info(f"✅ SUCCESSFULLY LINKED: {clean_name} to Movie {tmdb_id}")
            return True
            
        except Exception as e:
            logger.error(f"TRANSFER FAILURE for TMDB {tmdb_id}: {e}")
            return False
