# apps/worker-video/handlers/leech.py
import os
import time
import logging
import PTN
import uuid
import aiohttp
import asyncio
from pyrogram import Client, enums
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from pyrogram.file_id import FileId
from handlers.processor import processor
from handlers.formatter import formatter 

logger = logging.getLogger("Leecher")

class MediaLeecher:
    def __init__(self, client, db):
        self.client = client
        self.db = db
        # Env feature flags
        self.gen_samples = os.getenv("GENERATE_SAMPLES", "True").lower() == "true"
        self.tmdb_api_key = os.getenv("TMDB_API_KEY", "your_key_here") # Ensure this is set
        
        try:
            self.log_channel = int(os.getenv("TG_LOG_CHANNEL_ID", "0"))
            self.backup_channel = int(os.getenv("TG_BACKUP_CHANNEL_ID", "0"))
        except:
            self.log_channel = 0
            self.backup_channel = 0

    async def fetch_metadata_if_missing(self, tmdb_id: int):
        """Auto-Indexes TMDB Content if DB entry is empty (The Fix)"""
        if not self.tmdb_api_key or self.tmdb_api_key == "your_key_here":
            return None # API Key missing
        
        try:
            async with aiohttp.ClientSession() as sess:
                # 1. Try Movie
                url = f"https://api.themoviedb.org/3/movie/{tmdb_id}?api_key={self.tmdb_api_key}"
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "tmdb_id": tmdb_id,
                            "media_type": "movie",
                            "title": data.get('title'),
                            "year": (data.get('release_date', '') or '0000')[:4],
                            "genres": [g['name'] for g in data.get('genres', [])],
                            "rating": data.get('rating', 0.0),
                            "overview": data.get('overview', '')
                        }
                    
                # 2. Try TV Show (Fallback)
                url_tv = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={self.tmdb_api_key}"
                async with sess.get(url_tv) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "tmdb_id": tmdb_id,
                            "media_type": "tv",
                            "title": data.get('name'),
                            "year": (data.get('first_air_date', '') or '0000')[:4],
                            "genres": [g['name'] for g in data.get('genres', [])],
                            "rating": data.get('rating', 0.0),
                            "overview": data.get('overview', '')
                        }
        except Exception as e:
            logger.error(f"Metadata Auto-Fetch Failed: {e}")
        return None

    async def upload_progress(self, current, total):
        if total > 0:
            pct = int(current * 100 / total)
            # Safe checking for _last_log attribute
            if pct % 20 == 0 and pct != getattr(self, '_last_log', -1):
                logger.info(f"📤 Upload: {pct}%")
                self._last_log = pct

    async def upload_and_sync(self, file_path: str, tmdb_id: int):
        cleanup_targets = [file_path] # Files to delete at end
        
        try:
            # 1. Fetch DB Meta (For the beautiful caption)
            db_item = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})

            # If missing in DB, FETCH IT NOW
            if not db_item:
                logger.info(f"⚠️ Metadata missing for #{tmdb_id}. Auto-fetching...")
                meta_from_tmdb = await self.fetch_metadata_if_missing(int(tmdb_id))
                
                if meta_from_tmdb:
                    db_item = meta_from_tmdb
                    db_item["short_id"] = str(uuid.uuid4())[:7]
                    db_item["status"] = "indexing"
                    # We save it immediately so next files use it
                    await self.db.library.insert_one(db_item.copy())
                else:
                    # Final Fail Safe
                    db_item = {
                        "tmdb_id": int(tmdb_id),
                        "title": os.path.basename(file_path),
                        "vote_average": 0.0,
                        "year": 2026,
                        "genres": [],
                        "short_id": str(uuid.uuid4())[:7],
                        "visuals": {}
                    }

            # 2. Probe Media (Processor)
            meta = await processor.probe(file_path)
            duration = meta.get('duration', 0)
            
            # 3. Prepare Visuals
            clean_caption = formatter.build_caption(
                tmdb_id, 
                meta, 
                os.path.basename(file_path), 
                db_entry=db_item
            )
            buttons = formatter.build_buttons(db_item.get('short_id', ''))

            # 4. Generate Assets
            screenshots = []
            sample_path = None
            if duration > 0:
                # Screenshots
                screenshots = await processor.generate_screenshots(file_path, duration)
                cleanup_targets.extend(screenshots)

                # Sample
                if self.gen_samples and duration > 120:
                    sample_path = await processor.generate_sample(file_path, duration)
                    if sample_path: cleanup_targets.append(sample_path)

            # 5. Main Upload (With Fancy Caption)
            logger.info("🚀 Uploading Main Video...")
            self._last_log = -1
            
            video_msg = await self.client.send_document(
                chat_id=self.log_channel,
                document=file_path,
                caption=clean_caption, # <--- The Professional Text
                reply_markup=buttons,
                force_document=True,
                progress=self.upload_progress
            )

            # Store the Video Message ID securely
            main_msg_id = video_msg.id
            main_file_id = video_msg.document.file_id

             # --- 🔗 GENERATE MESSAGE LINK  ---
            # Telegram format: https://t.me/c/{CHANNEL_ID}/{MSG_ID}
            # Note: Must strip the "-100" prefix for the link to work
            clean_chat_id = str(self.log_channel).replace("-100", "")
            msg_link = f"https://t.me/c/{clean_chat_id}/{main_msg_id}"
            
            # Create a rich caption for assets
            asset_caption = (
                f"📸 **Gallery: {db_item.get('title')}**\n"
                f"🆔 TMDB: `{tmdb_id}`\n"
                f"📎 [Go to Main File]({msg_link})"
            )

            # 6. Mirroring (Redundancy)
            if self.backup_channel != 0:
                try:
                    await video_msg.forward(self.backup_channel)
                    logger.info("🛡️ Video Mirrored")
                except Exception as e:
                    logger.warn(f"Mirror failed: {e}")

            # 7. Asset Album Upload
            media_group = []

            # 7.1. Add Sample if exists
            if sample_path:
                media_group.append(InputMediaVideo(sample_path)) # Add without caption first

            # 7.2. Add Screenshots
            for s in screenshots:
                media_group.append(InputMediaPhoto(s))

            screen_file_ids = []

            if media_group:
                # Attach caption to the FIRST item only
                # Telegram albums display the caption of the first item as the "Album Caption"
                media_group[0].caption = asset_caption
                
                logger.info("📤 Uploading Assets Album...")
                try:
                   # A: Send to LOG CHANNEL (With Reply to Video)
                    album_msgs = await self.client.send_media_group(
                        chat_id=self.log_channel,
                        media=media_group,
                        reply_to_message_id=main_msg_id # Creates the thread logic
                    )

                    # Capture Data for Forwarding
                    msg_ids_to_forward = [m.id for m in album_msgs]

                    # Capture File IDs for DB (Screenshots only)
                    for m in album_msgs:
                        if m.photo: screen_file_ids.append(m.photo.file_id)

                    # B: FORWARD TO BACKUP CHANNEL (Safety Copy)
                    # We forward the album we just sent
                    if self.backup_channel != 0 and msg_ids_to_forward:
                        await self.client.forward_messages(
                            chat_id=self.backup_channel,
                            from_chat_id=self.log_channel,
                            message_ids=msg_ids_to_forward
                        )
                        logger.info(f"🛡️ Album Mirrored ({len(msg_ids_to_forward)} parts)")

                except Exception as e:
                    logger.error(f"Asset/Album error: {e}")

            # 8. Database Indexing (Final Save)
            doc = video_msg.document
            decoded = FileId.decode(doc.file_id)
            
            # Format: Pydantic Compliant Audio/Subs
            db_file_entry = {
                "quality": PTN.parse(file_path).get('quality', 'HD'),
                "telegram_id": doc.file_id, # Stores VIDEO id only
                "location_id": main_msg_id, # Stores Message ID for Streaming headers
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "tg_raw": {
                    "media_id": decoded.media_id,
                    "access_hash": decoded.access_hash,
                    "file_reference": decoded.file_reference.hex()
                },
                "subtitles": meta.get('subtitles', []),
                "audio_tracks": meta.get('audio', []), # New Schema Field
                "added_at": int(time.time())
            }

            # Update DB (Using Logic A/B)
            # IMPORTANT: Re-query incase auto-fetch inserted the document
            existing_final = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})

            if existing_final:
                await self.db.library.update_one(
                    {"_id": existing_final["_id"]},
                    {"$push": {"files": db_file_entry}, 
                     "$set": {"visuals.screenshots": screen_file_ids, "status": "available"}}
                )
            else:
                # Should not happen given logic in Step 1, but failsafe:
                new_doc = {
                    "tmdb_id": int(tmdb_id),
                    "short_id": str(uuid.uuid4())[:7],
                    "title": "Indexed Upload",
                    "status": "available",
                    "visuals": { "screenshots": screen_file_ids },
                    "files": [db_file_entry]
                }
                await self.db.library.insert_one(new_doc)

            logger.info(f"✅ Indexed Complete: {tmdb_id}")
            return True

        except Exception as e:
            logger.error(f"Critical Leech Fail: {e}")
            return False
        
        finally:
            # 9. Aggressive Cleanup (Critical for Dev Mode)
            # We add a small sleep to ensure Pyrogram has released file handles
            await asyncio.sleep(0.5)
            for f in cleanup_targets:
                if f and os.path.exists(f): 
                    try: os.remove(f)
                    except: pass
            logger.info("🧹 Cleaned.")
