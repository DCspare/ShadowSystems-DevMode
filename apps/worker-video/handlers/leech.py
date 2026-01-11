# apps/worker-video/handlers/leech.py
import os
import time
import logging
import PTN
import uuid
import asyncio
from pyrogram import Client, enums
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.file_id import FileId
from handlers.processor import processor

logger = logging.getLogger("Leecher")

class MediaLeecher:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        self.branding = os.getenv("FILE_BRANDING_TAG", "[ShadowSystems]")
        
        # Channels
        try:
            self.log_channel = int(os.getenv("TG_LOG_CHANNEL_ID", "0"))
            self.backup_channel = int(os.getenv("TG_BACKUP_CHANNEL_ID", "0"))
        except:
            self.log_channel = 0
            self.backup_channel = 0

        # Features
        self.gen_samples = os.getenv("GENERATE_SAMPLES", "True").lower() == "true"

    def sanitize_title(self, raw_name: str) -> str:
        try:
            info = PTN.parse(raw_name)
            title = info.get('title', 'Unknown')
            if not title or len(title) < 3: return f"{self.branding} {raw_name}"
            year = f" ({info.get('year')})" if info.get('year') else ""
            quality = f" {info.get('quality')}" if info.get('quality') else ""
            return f"{self.branding} {title}{year}{quality}"
        except:
            return f"{self.branding} {raw_name}"

    async def upload_progress(self, current, total):
        if total > 0:
            percentage = current * 100 / total
            if int(percentage) % 10 == 0 and int(percentage) != getattr(self, '_last_log_pct', -1):
                logger.info(f"📤 Uploading Main: {percentage:.1f}%")
                self._last_log_pct = int(percentage)

    async def upload_and_sync(self, file_path: str, tmdb_id: int):
        # Tracker for cleanup
        generated_files = []
        
        try:
            file_name = os.path.basename(file_path)
            clean_name = self.sanitize_title(file_name)
            logger.info(f"⚙️ Processing Media: {file_name}")

            # 1. FFmpeg Probe (Subtitles & Meta)
            meta = await processor.probe(file_path)
            duration = meta.get('duration', 0)
            subtitles = meta.get('subtitles', []) # Now we have subtitle indices!
            
            # 2. Asset Generation (Screenshots & Sample)
            screenshots = []
            sample_file = None
            
            # Screenshots
            if duration > 0:
                screenshots = await processor.generate_screenshots(file_path, duration)
                generated_files.extend(screenshots)
            
            # Sample Clip (if enabled and file long enough)
            if self.gen_samples and duration > 120:
                sample_file = await processor.generate_sample(file_path, duration)
                if sample_file: generated_files.append(sample_file)

            # 3. Main File Upload
            logger.info(f"🚀 Uploading Video...")
            self._last_log_pct = -1
            
            video_msg = await self.client.send_document(
                chat_id=self.log_channel,
                document=file_path,
                file_name=f"{clean_name}{os.path.splitext(file_name)[1]}",
                caption=f"🎥 **{clean_name}**\n⏱️ `{int(duration)}s` | 💾 `{os.path.getsize(file_path) // (1024*1024)}MB`",
                force_document=True,
                progress=self.upload_progress
            )

             # Store the Video Message ID securely
            main_msg_id = video_msg.id
            main_file_id = video_msg.document.file_id

            # 4. Shadow Mirror (Redundancy)
            # Instant backup forwarding before processing data
            if self.backup_channel != 0:
                try:
                    await video_msg.forward(self.backup_channel)
                    logger.info("🛡️ Mirrored to Backup Channel")
                except Exception as e:
                    logger.warning(f"Mirror failed: {e}")

            # 5. Asset Album Upload (Reply to Main Video)
            # This separates visuals from the video file in the DB logic
            screen_file_ids = []
            media_group = []
            
            if screenshots:
                for s in screenshots:
                    media_group.append(InputMediaPhoto(s))
            if sample_file:
                media_group.append(InputMediaVideo(sample_file, caption="🔍 30s Verification Sample"))

            if media_group:
                logger.info("📤 Uploading Assets Album...")
                try:
                    album_msgs = await self.client.send_media_group(
                        chat_id=self.log_channel,
                        media=media_group,
                        reply_to_message_id=video_msg.id
                    )
                    # Extract IDs from the album message(s)
                    for m in album_msgs:
                        if m.photo: screen_file_ids.append(m.photo.file_id)
                except Exception as e:
                    logger.error(f"Asset upload failed: {e}")

            # 6. Database Indexing
            doc = video_msg.document
            decoded = FileId.decode(doc.file_id)
            
            # Convert FFmpeg subs to DB schema format
            db_subs = []
            for s in subtitles:
                db_subs.append({"lang": str(s['lang']), "index": int(s['index'])})

            file_data = {
                "quality": PTN.parse(file_name).get('quality', '720p'),
                "telegram_id": main_file_id, # Stores VIDEO id only
                "location_id": main_msg_id, # Stores Message ID for Streaming headers
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "tg_raw": {
                    "media_id": decoded.media_id,
                    "access_hash": decoded.access_hash,
                    "file_reference": decoded.file_reference.hex()
                },
                "subtitles": db_subs,
                "added_at": int(time.time())
            }

            # Upsert Logic
            existing = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})
            
            if existing:
                await self.db.library.update_one(
                    {"_id": existing["_id"]},
                    {"$push": {"files": file_data}, 
                     "$set": {"status": "available", "visuals.screenshots": screen_file_ids}}
                )
                logger.info(f"✅ DB UPDATED: {tmdb_id}")
            else:
                # Skeleton
                new_doc = {
                    "tmdb_id": int(tmdb_id),
                    "title": f"Processing Upload {tmdb_id}",
                    "clean_title": f"upload {tmdb_id}",
                    "short_id": str(uuid.uuid4())[:7],
                    "media_type": "movie",
                    "status": "available",
                    "visuals": { "poster": None, "screenshots": screen_file_ids },
                    "files": [file_data]
                }
                await self.db.library.insert_one(new_doc)
                logger.info(f"✅ DB INSERTED: {tmdb_id}")

            return True

        except Exception as e:
            logger.error(f"❌ Worker Logic Fail: {e}")
            return False
        
        finally:
            # 7. CLEANUP EVERYTHING (Critical for Dev Mode)
            try:
                for f in generated_files:
                    if os.path.exists(f): os.remove(f)
                # if os.path.exists(file_path):
                #     os.remove(file_path)
                # logger.info("🧹 Temp files scrubbed.")
            except:
                pass