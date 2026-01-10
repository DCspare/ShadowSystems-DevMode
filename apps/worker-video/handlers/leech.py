import os
import time
import logging
import PTN
import uuid
from pyrogram.file_id import FileId

logger = logging.getLogger("Leecher")

class MediaLeecher:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.branding = os.getenv("FILE_BRANDING_TAG", "[ShadowSystem]")

    def sanitize_title(self, raw_name: str) -> str:
        try:
            info = PTN.parse(raw_name)
            title = info.get('title', 'Unknown')
            return f"{self.branding} {title}"
        except:
            return f"{self.branding} {raw_name}"

    async def get_log_chat(self):
        try:
            return int(os.getenv("TG_LOG_CHANNEL_ID"))
        except:
            return 0

    async def upload_progress(self, current, total):
        if total > 0:
            percentage = current * 100 / total
            if int(percentage) % 10 == 0 and int(percentage) != getattr(self, '_last_log_pct', -1):
                logger.info(f"📤 Uploading: {percentage:.1f}%")
                self._last_log_pct = int(percentage)

    async def upload_and_sync(self, file_path: str, tmdb_id: int):
        try:
            log_channel = await self.get_log_chat()
            file_name = os.path.basename(file_path)
            clean_name = self.sanitize_title(file_name)
            
            logger.info(f"🚀 Starting Upload: {file_name}")
            self._last_log_pct = -1
            
            # Upload
            sent_msg = await self.client.send_document(
                chat_id=log_channel,
                document=file_path,
                file_name=f"{clean_name}{os.path.splitext(file_name)[1]}",
                caption=f"🎥 **{clean_name}**",
                force_document=True,
                progress=self.upload_progress
            )

            # --- KEY FIX: DECODING LOGIC ---
            doc = sent_msg.document
            decoded = FileId.decode(doc.file_id)
            
            file_data = {
                "quality": PTN.parse(file_name).get('quality', '720p'),
                "telegram_id": doc.file_id,
                # 🛡️ STORE LOCATION FOR REFRESHING
                "location_id": sent_msg.id,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "added_at": int(time.time()),
                "tg_raw": {
                    "media_id": decoded.media_id,
                    "access_hash": decoded.access_hash,
                    "file_reference": decoded.file_reference.hex()
                }
            }

            # Upsert Logic
            existing = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})
            
            if existing:
                await self.db.library.update_one(
                    {"_id": existing["_id"]},
                    {"$push": {"files": file_data}, "$set": {"status": "available"}}
                )
                logger.info(f"✅ DB UPDATED: {tmdb_id}")
            else:
                new_doc = {
                    "tmdb_id": int(tmdb_id),
                    "title": f"Upload {tmdb_id}",
                    "short_id": str(uuid.uuid4())[:7],
                    "media_type": "movie",
                    "status": "available",
                    "visuals": { "poster": None },
                    "files": [file_data]
                }
                await self.db.library.insert_one(new_doc)
                logger.info(f"✅ DB INSERTED: {tmdb_id}")

            return True
            
        except Exception as e:
            logger.error(f"Upload Logic Fail: {e}")
            return False
