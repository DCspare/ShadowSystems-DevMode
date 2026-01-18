# apps/worker-video/handlers/flow_ingest.py (formerly leech.py)
import os
import sys
import PTN
import time
import logging
import uuid
import aiohttp
import asyncio
sys.path.append("/app/shared")
from pyrogram import Client, enums
from shared.settings import settings
from pyrogram.file_id import FileId
from handlers.processor import processor
from shared.formatter import formatter 
from pyrogram.types import InputMediaPhoto, InputMediaVideo

logger = logging.getLogger("Leecher")

class MediaLeecher:
    def __init__(self, client, db):
        self.client = client
        self.db = db

        # ✨ CLEAN CONFIG USAGE
        self.gen_samples = settings.GENERATE_SAMPLES
        self.tmdb_api_key = settings.TMDB_API_KEY
        self.branding = settings.FILE_BRANDING_TAG
        
        try:
            self.log_channel = settings.TG_LOG_CHANNEL_ID
            self.backup_channel = settings.TG_BACKUP_CHANNEL_ID
        except:
            self.log_channel = 0
            self.backup_channel = 0

    def sanitize_url(self, url):
        """Removes api_key from logs"""
        if "api_key=" in url:
            return url.split("api_key=")[0] + "api_key=***HIDDEN***"
        return url

    async def get_episode_details(self, tmdb_id: int, season: int, episode: int):
        """Fetches Specific Episode Title with enhanced logging"""
        if not self.tmdb_api_key or season == 0 or episode == 0: 
            return None
        
        try:
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{season}/episode/{episode}?api_key={self.tmdb_api_key}"
            logger.info(f"🔎 Checking Episode Metadata: {self.sanitize_url(url)}")
            
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        ep_data = await resp.json()
                        title = ep_data.get('name')
                        logger.info(f"✅ Found Ep Title: {title}")
                        return {
                            'name': ep_data.get('name'),
                            'still_path': ep_data.get('still_path'),
                            'overview': ep_data.get('overview', '') # ➕ 
                        }
                    else:
                        logger.warning(f"❌ TMDB Ep Error {resp.status}")
        except Exception as e:
            logger.error(f"Episode fetch failed: {e}")
            
        return None

    async def normalize_episode_mapping(self, tmdb_id: int, ptn_data: dict, media_type: str, raw_filename: str):
        """
        Translates File Numbering -> TMDB Numbering.
        Specifically for Anime which uses Absolute numbers (Ep 1050)
        while TMDB breaks them into Seasons (Season 21 Ep 12).
        """
        s_num = ptn_data.get('season')
        e_num = ptn_data.get('episode')

        # FALLBACK: If PTN fails but we see "S02" in text, force it
        if s_num is None:
            import re
            # Regex to find Sxx or Season xx
            s_match = re.search(r'(?i)S(\d{1,2})', raw_filename)
            if s_match: s_num = int(s_match.group(1))

        if e_num is None:
             # Regex to find Exx or Episode xx
            e_match = re.search(r'(?i)E(\d{1,3})', raw_filename)
            if e_match: e_num = int(e_match.group(1))

       # CASE A: Western
        if media_type in ['tv', 'series']:
            final_season = s_num if s_num is not None else 1
            return final_season, e_num, {}

            # CASE B: Anime
        if media_type in ['anime', 'anime_movie']:
            if s_num is not None: return s_num, e_num, {}
            return 1, e_num, {}

        return s_num, e_num, {}

    async def fetch_metadata_if_missing(self, content_id: int, file_name_hint: str = "", type_hint: str = "auto"):
        """
        Smart Auto-Indexer: 
        1. Checks TMDB Movie.
        2. Checks TMDB TV (Series).
        3. Checks Jikan (MAL) for Anime fallback.
        Priority is determined by 'type_hint' or detected via SxxExx patterns.
        """
        if not self.tmdb_api_key or len(self.tmdb_api_key) < 5:
            return None 
        
        # 1. Strategy Determination
        search_order = []
        
        # Parse Filename for SxxExx pattern
        parsed = PTN.parse(file_name_hint)
        is_series_file = bool(parsed.get('season') or parsed.get('episode'))

        # A. Explicit Hints (from Command)
        if type_hint in ["tv", "series", "show"]:
            search_order = ["tv"]
        elif type_hint in ["movie", "film"]:
            search_order = ["movie"]
        elif type_hint in ["anime", "mal"]:
            search_order = ["anime"]
        
        # B. Automatic Inference
        else: # type_hint == "auto"
            if is_series_file:
                search_order = ["tv", "movie", "anime"]
            else:
                search_order = ["movie", "tv", "anime"]

        logger.info(f"🔎 Metadata Search Order: {search_order}")

        async with aiohttp.ClientSession() as sess:
            for media_type in search_order:

                # --- CASE 1: ANIME (Jikan/MAL) ---
                if media_type == "anime":
                    url_mal = f"https://api.jikan.moe/v4/anime/{content_id}"
                    async with sess.get(url_mal) as resp:
                        if resp.status == 200:
                            mal_data = await resp.json()
                            d = mal_data['data']
                            logger.info(f"✅ Metadata Match: [ANIME] {d.get('title')}")
                            return {
                                "mal_id": content_id, # Uses MAL ID
                                "media_type": "anime",
                                "title": d.get('title_english') or d.get('title'),
                                "clean_title": (d.get('title') or "").lower(),
                                "year": str(d.get('year') or "0000"),
                                "genres": [g['name'] for g in d.get('genres', [])],
                                "rating": float(d.get('score') or 0.0),
                                "overview": d.get('synopsis', ''),
                                "status": "available",
                                "visuals": { "poster": d['images']['jpg']['large_image_url'] }
                            }
                    continue # Try next if failed
                        
            # --- CASE 2: TMDB (Movie/TV) ---
                url = f"https://api.themoviedb.org/3/{media_type}/{content_id}?api_key={self.tmdb_api_key}"
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Anime Check within TMDB (Heuristic)
                        is_anime_genre = 'ja' in data.get('original_language', '') and \
                                         any(g['name'] == 'Animation' for g in data.get('genres', []))
                        
                        final_type = media_type
                        if media_type == 'tv' and is_anime_genre: final_type = "anime"
                        elif media_type == 'movie' and is_anime_genre: final_type = "anime_movie"

                        title = data.get('title') if media_type == 'movie' else data.get('name')
                        year_raw = data.get('release_date') if media_type == 'movie' else data.get('first_air_date')
                        year = (year_raw or "0000")[:4]

                        logger.info(f"✅ Metadata Match: [{final_type.upper()}] {title}")

                        return {
                            "tmdb_id": content_id,
                            "media_type": final_type,
                            "title": title,
                            "clean_title": title.lower(),
                            "year": year,
                            "genres": [g['name'] for g in data.get('genres', [])],
                            "rating": data.get('vote_average', 0.0),
                            "overview": data.get('overview', ''),
                            "status": "available",
                            "visuals": {
                                "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else None,
                                "backdrop": f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get('backdrop_path') else None
                            }
                        }
        
        return None

    async def upload_progress(self, current, total):
        if total > 0:
            pct = int(current * 100 / total)
            # Safe checking for _last_log attribute
            if pct % 20 == 0 and pct != getattr(self, '_last_log', -1):
                logger.info(f"📤 Upload: {pct}%")
                self._last_log = pct

    async def upload_and_sync(self, file_path: str, tmdb_id: int, type_hint: str = "auto"):
        # SAFETY INIT: Variables must exist before TRY block
        current_file_path = file_path
        cleanup_targets = [file_path]
        
        try:
            file_name = os.path.basename(current_file_path)

            # 1. Fetch DB Meta (For the beautiful caption with Smart Fallback)
            db_item = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})

            # If missing in DB, FETCH IT NOW
            if not db_item:
                logger.info(f"⚠️ Metadata missing  Auto-fetch mode: {type_hint} for #{tmdb_id}.")

                # [CHANGE]: Passing the typye_hint ('tv', 'movie', 'anime', or 'auto')
                meta_from_tmdb = await self.fetch_metadata_if_missing(int(tmdb_id), file_name, type_hint)
                
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
                        "title": file_name,
                        "ratng": 0.0,
                        "year": 2026,
                        "genres": [],
                        "short_id": str(uuid.uuid4())[:7],
                        "media_type": "unknown",
                        "visuals": {}
                    }

            # 2. Probe Media (Processor)
            meta = await processor.probe(current_file_path)
            duration = meta.get('duration', 0)

            # 2.5 Resolve Episode Data
            # PTN (Parse name) -> Check if DB Item is a Series -> Get Ep Details
            
            ptn = PTN.parse(file_name)
            
            # We check the NEWLY FETCHED db_item media type here to detect if it's a series or anime
            ep_meta = {}
            if db_item.get('media_type') in ['series', 'anime', 'tv'] and ptn.get('season') and ptn.get('episode'):
                 ep_details = await self.get_episode_details(tmdb_id, ptn.get('season'), ptn.get('episode'))
                 if ep_details:
                     ep_meta = {
                         'name': ep_details.get('name'),
                         'still_path': ep_details.get('still_path'),
                         'overview': ep_details.get('overview')
                     }

            # --- BRANDED RENAMING LOGIC ---
            ext = os.path.splitext(file_name)[1]
            # Construct: Title.S01E01.720p.[ShadowSystem].mp4
            # We sanitize spaces to dots for clean file names
            safe_title = ptn.get('title', 'Video').replace(' ', '.')
            quality_tag = ptn.get('quality', 'HD')
            
            s_tag = ""
            if ptn.get('season') and ptn.get('episode'):
                s_tag = f".S{ptn.get('season'):02d}-E{ptn.get('episode'):02d}"
                
            branded_name = f"{safe_title}{s_tag}.{quality_tag}.{self.branding}{ext}"
            
            # Perform Rename
            new_path = os.path.join(os.path.dirname(file_path), branded_name)
            os.rename(file_path, new_path)
            file_path = new_path
            file_name = branded_name
            
            logger.info(f"🏷️ Branded as: {file_name}")
            
            # 3. Prepare Visuals
            clean_caption = formatter.build_caption(
                tmdb_id, 
                meta, 
                file_name, 
                db_entry=db_item,
                episode_meta=ep_meta # <--- PASS THIS TO FORMATTER
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

            # 6. Mirroring (Backup)
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
            
            ptn = PTN.parse(file_name)
            
            # --- STRUCTURE 1: The Raw File Data (All Media Types) ---
            db_file_entry = {
                "quality": ptn.get('quality', '720p'),
                "telegram_id": doc.file_id, # Stores VIDEO id only
                "location_id": main_msg_id, # Stores Message ID for Streaming headers
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                # Store detected season info here for flat filtering too
                "tg_raw": {
                    "media_id": decoded.media_id,
                    "access_hash": decoded.access_hash,
                    "file_reference": decoded.file_reference.hex()
                },
                "subtitles": meta.get('subtitles', []),
                "audio_tracks": meta.get('audio', []), # Maps from processor output
                "embeds": [],    # Populated by separate "Daisy Chain" job later
                "downloads": [], 
                "added_at": int(time.time())
            }

            # Update Op Generator
            existing_final = await self.db.library.find_one({"tmdb_id": int(tmdb_id)})

            # 1. Update the Main File List
            update_ops = {
                "$push": {"files": db_file_entry}, 
                "$set": {
                    "visuals.screenshots": screen_file_ids, 
                    "status": "available",
                    # Refresh Date so it bubbles to top of 'Recently Added'
                    "last_updated": int(time.time()) 
                }
            }
                
            # --- STRUCTURE 2: The Seasonal Mapper (Logic Upgrade) ---
            # Use the media_type from the DB (populated by auto-fetch)
            current_media_type = existing_final.get('media_type', 'movie') if existing_final else "movie"
            
            s_num, e_num, _ = await self.normalize_episode_mapping(int(tmdb_id), ptn, current_media_type, file_name)
            
            # Only index as Series if we have valid Episode Data
            if e_num is not None:
                ep_obj = {
                     "episode": e_num,
                     "title": ep_meta.get('name', f"Episode {e_num}"),
                     "overview": ep_meta.get('overview', ''),
                     "still_path": ep_meta.get('still_path', None),
                     "file_id": doc.file_id,
                     "quality": ptn.get('quality', '720p'),
                     # Useful for distinguishing "File X" from "File Y" in UI
                     "unique_hash": decoded.media_id 
                 }
                 
            # Key Point: Push to "seasons.1", "seasons.2", etc.
            if e_num is not None:

                update_ops["$push"][f"seasons.{s_num}"] = ep_obj

                # Safety: Set total_seasons count if this is a new high score
                # This requires an aggregation pipeline technically, but simplistic:
                # We update it to at least the current season
                update_ops["$max"] = {"total_seasons": s_num}
                
               # EXECUTE WRITE
            if existing_final:
                await self.db.library.update_one(
                    {"_id": existing_final["_id"]},
                    update_ops
                )
            else:
                # Skeleton
                new_doc = {
                    "tmdb_id": int(tmdb_id),
                    "short_id": str(uuid.uuid4())[:7],
                    "title": os.path.basename(file_path),
                    "media_type": "series" if e_num else "movie",
                    "status": "available",
                    "visuals": { "screenshots": screen_file_ids },
                    "files": [db_file_entry],
                    "total_seasons": s_num if s_num else 1,
                    "seasons": {}
                }
                if e_num: new_doc["seasons"] = { str(s_num): [ep_obj] }
                await self.db.library.insert_one(new_doc)
            
            logger.info(f"✅ Index Complete | Series: {bool(e_num)} (S{s_num}E{e_num})")
            return True

        except Exception as e:
            logger.error(f"Critical Leech Fail: {e}")
            return False
        
        finally:
            # 9. Robust Cleanup
            # Force close potential pyrogram file handlers by waiting a moment
            await asyncio.sleep(2.0)

            # Master List: Init path + Current path + Screenshots
            targets = set(cleanup_targets)
            if 'current_file_path' in locals():
                targets.add(current_file_path)
            
            logger.info(f"🧹 Scrubbing {len(targets)} items...")

            for f in targets:
                # Resolve Absolute Path just in case
                abs_path = os.path.abspath(f)
                
                if os.path.exists(abs_path): 
                    try:
                        # Attempt standard remove
                        os.remove(abs_path)
                    except Exception as e:
                        logger.error(f"❌ Failed to delete {os.path.basename(abs_path)}: {e}")
            
            logger.info("✅ Cleanup phase done.")
