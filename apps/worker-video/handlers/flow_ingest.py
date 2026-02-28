# apps/worker-video/handlers/flow_ingest.py (formerly leech.py)
import logging
import os
import re
import sys
import time
import uuid

import PTN

sys.path.append("/app/shared")
from pyrogram import StopTransmission
from pyrogram.file_id import FileId
from pyrogram.types import InputMediaPhoto, InputMediaVideo
from services.metadata_service import MetadataService

from handlers.processor import processor
from shared.database import db_service
from shared.formatter import formatter
from shared.progress import TaskProgress
from shared.registry import MirrorStatus, task_dict, task_dict_lock
from shared.settings import settings
from shared.tg_client import TgClient

logger = logging.getLogger("Leecher")


class MediaLeecher:
    def __init__(self, client, db, redis=None):
        self.client = client
        self.db = db
        # Use passed redis, fallback to shared service singleton
        self.redis = redis or db_service.redis
        self.last_edit_time = 0  # <--- Track time for throttling
        self.is_cancelled = False

        # ✨ CLEAN CONFIG USAGE
        self.tmdb_api_key = settings.TMDB_API_KEY
        self.meta_service = MetadataService(self.tmdb_api_key)

        self.gen_samples = settings.GENERATE_SAMPLES
        self.branding = settings.FILE_BRANDING_TAG

        try:
            self.log_channel = settings.TG_LOG_CHANNEL_ID
            self.backup_channel = settings.TG_BACKUP_CHANNEL_ID
        except:
            self.log_channel = 0
            self.backup_channel = 0

    async def normalize_episode_mapping(
        self, tmdb_id: int, ptn_data: dict, media_type: str, raw_filename: str
    ):
        """
        Translates File Numbering -> TMDB Numbering.
        Specifically for Anime which uses Absolute numbers (Ep 1050)
        while TMDB breaks them into Seasons (Season 21 Ep 12).
        """
        # 🛡️ THE CIRCUIT BREAKER: Force exit for any Movie type
        if media_type in ["movie", "anime_movie"]:
            logger.info(
                f"🚫 Circuit Breaker: {media_type} detected. Skipping episode mapping."
            )
            return None, None, {}

        s_num = ptn_data.get("season")
        e_num = ptn_data.get("episode")

        # FALLBACK: If PTN fails but we see "S02" in text, force it
        if s_num is None:
            # Regex to find Sxx or Season xx
            s_match = re.search(r"(?i)S(\d{1,2})", raw_filename)
            if s_match:
                s_num = int(s_match.group(1))

        if e_num is None:
            # Regex to find Exx or Episode xx
            e_match = re.search(r"(?i)E(\d{1,3})", raw_filename)
            if e_match:
                e_num = int(e_match.group(1))

        # CASE A: Western / General
        if media_type in ["tv", "series"]:
            final_season = s_num if s_num is not None else 1
            return final_season, e_num, {}

        # CASE B: Anime
        if media_type == "anime":
            if s_num is not None:
                return s_num, e_num, {}
            return 1, e_num, {}

        return s_num, e_num, {}

    async def upload_progress(self, current, total):
        if total <= 0:
            return

        # 1. Always update Redis (for the /status command)
        if hasattr(self, "current_task_id") and self.current_task_id:
            # 2. Update SHARED REGISTRY (For StatusManager UI)
            task = task_dict.get(self.current_task_id)
            if task:
                # WZML-X Logic: Inject progress into the Status Object
                if hasattr(task, "update_progress"):
                    task.update_progress(
                        current, total, status=MirrorStatus.STATUS_UPLOADING
                    )
                elif hasattr(task, "status_obj") and task.status_obj:
                    task.status_obj.update_progress(
                        current, total, status=MirrorStatus.STATUS_UPLOADING
                    )

                # Terminal Heartbeat (Every 20%)
                pct_int = int(current * 100 / total)
                if pct_int % 20 == 0 and pct_int != getattr(
                    self, "_last_terminal_pct", -1
                ):
                    self._last_terminal_pct = pct_int
                    ui = task.get_ui_dict()
                    logger.info(
                        f"📤 [UPLOAD] {pct_int}% | {ui['speed']} | ETA: {ui['eta']} | ID: {self.current_task_id}"
                    )

            # 4. MID-UPLOAD KILL SWITCH (Pyrogram Native) ---
            kill_check = await self.redis.get(f"kill_signal:{self.current_task_id}")
            if kill_check:
                logger.warning(
                    f"🛑 Kill signal received during upload for {self.current_task_id}!"
                )
                # This is the official way to stop Pyrogram without socket errors
                raise StopTransmission("ABORTED_BY_SIGNAL")

    async def upload_and_sync(
        self,
        file_path: str,
        tmdb_id: int,
        type_hint: str = "auto",
        task_id: str = None,
        user_id: str = "0",
        origin_chat_id: int = None,
        trigger_msg_id: str = None,
        user_tag: str = "User",
        name_hint: str = "",
        swarm_idx=None,  # Track which bot we use
    ):
        # SAFETY INIT: Variables must exist before TRY block
        self.current_task_id = task_id
        self.current_user_id = user_id
        self.current_user_tag = user_tag  # Store for notifications
        self.trigger_msg_id = trigger_msg_id
        # Use origin if provided, fallback to default log channel
        self.notify_chat = origin_chat_id or self.log_channel
        self.is_cancelled = False  # Reset state

        current_file_path = file_path
        cleanup_targets = [file_path]

        # Initialize Tracker
        file_size = os.path.getsize(file_path)
        self.upload_tracker = TaskProgress(file_size)

        try:
            # 1. Kill Switch Check (Before Starting)
            if task_id and self.redis:
                # Check if user cancelled while we were downloading
                is_killed = await self.redis.get(f"kill_signal:{task_id}")
                if is_killed:
                    logger.info(f"🛑 Kill signal detected for {task_id}. Aborting.")
                    raise Exception("TASK_CANCELLED_BY_USER")

                # PICK SWARM CLIENT
                # Instead of self.client, we use a helper bot
                upload_client, swarm_idx = await TgClient.get_swarm_client()
                logger.info(f"🐝 Swarm Selection: Using Helper {swarm_idx or 'Main'}")

                # Update status to 'uploading'
                await self.redis.hset(f"task_status:{task_id}", "status", "uploading")

            file_name = os.path.basename(current_file_path)

            # 2. SMART DB CHECK (Look for ID AND verify the Media Type)
            # We create a query that respects the user's intent (Movie vs TV)
            query = {"$or": [{"tmdb_id": int(tmdb_id)}, {"mal_id": int(tmdb_id)}]}

            if type_hint in ["movie", "film"]:
                query["media_type"] = {"$in": ["movie", "anime_movie"]}
            elif type_hint in ["tv", "series", "show", "anime", "mal"]:
                query["media_type"] = {"$in": ["tv", "series", "anime"]}

            db_item = await self.db.library.find_one(query)

            # 3. METADATA FETCHING (The Enriched Version)
            if not db_item:
                logger.info(
                    f"⚠️ Metadata not in DB for ID {tmdb_id} ({type_hint}). Fetching from API..."
                )

                # Route to correct Service method
                if type_hint in ["anime", "mal"]:
                    meta_from_api = await self.meta_service.fetch_jikan_anime(
                        int(tmdb_id)
                    )
                elif type_hint in ["movie", "film"]:
                    meta_from_api = await self.meta_service.fetch_tmdb_movie(
                        int(tmdb_id)
                    )
                else:  # tv, series, show, or auto-detected tv
                    meta_from_api = await self.meta_service.fetch_tmdb_tv(int(tmdb_id))

                if meta_from_api:
                    db_item = meta_from_api
                    db_item["short_id"] = str(uuid.uuid4())[:7]
                    db_item["db_status"] = "available"  # Internal Status
                    # Create the skeleton
                    res = await self.db.library.insert_one(db_item.copy())
                    db_item["_id"] = res.inserted_id  # Capture the unique ID
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
                        "visuals": {},
                    }
                    res = await self.db.library.insert_one(db_item.copy())
                    db_item["_id"] = res.inserted_id  # Ensure we have the new ID

            # 🚀 4. FIX HEARTBEAT LAG (Update Status Name Now)
            async with task_dict_lock:
                task = task_dict.get(self.current_task_id)
                if task:
                    # Check if it's a status object with a listener
                    if hasattr(task, "_listener"):
                        task._listener.name = db_item.get("title", file_name)
                    # Fallback for raw listeners
                    elif hasattr(task, "name") and not callable(task.name):
                        task.name = db_item.get("title", file_name)
                    logger.info(
                        f"✨ Status Heartbeat updated to: {db_item.get('title')}"
                    )

            # 5. Probe Media (Processor)
            meta = await processor.probe(current_file_path)
            duration = meta.get("duration", 0)

            # 2.5 Resolve Episode Data
            # PTN (Parse name) -> Check if DB Item is a Series -> Get Ep Details

            # Prioritize parsing the name_hint (e.g. "The Night Manager S01E04")
            # over the raw download URL/filename.
            parse_target = name_hint if name_hint else file_name
            ptn = PTN.parse(parse_target)

            # We check the NEWLY FETCHED db_item media type here to detect if it's a series or anime
            ep_meta = {}
            if db_item.get("media_type") in ["series", "tv"] and db_item.get("tmdb_id"):
                s_num = ptn.get("season")
                e_num = ptn.get("episode")

                if s_num is not None and e_num is not None:
                    # Fetch details from TMDB
                    ep_details = await self.meta_service.fetch_show_episode_meta(
                        db_item["tmdb_id"], s_num, e_num
                    )
                    if ep_details:
                        ep_meta = {
                            "name": ep_details.get("name"),
                            "season": s_num,
                            "episode": e_num,
                        }
            # Fallback: If it's an Anime or TMDB failed, just use PTN numbers
            if not ep_meta and ptn.get("episode"):
                ep_meta = {
                    "season": ptn.get("season") or 1,
                    "episode": ptn.get("episode"),
                }

            # --- BRANDED RENAMING LOGIC ---
            # Construct: Title.S01E01.720p.[ShadowSystem].mp4
            ext = os.path.splitext(file_name)[1]

            # 1. Determine the best Title
            # Priority: 1. TMDB Title (Monster) | 2. PTN Guess | 3. Fallback "Video"
            db_title = db_item.get("title")
            ptn_title = ptn.get("title")

            # Priority: 1. TMDB Title, 2. Filename Title, 3. "Video"
            best_title = db_item.get("title") or ptn.get("title") or "Video"

            # 2. Sanitize for Filesystem (Dots instead of spaces)
            safe_title = best_title.replace(" ", ".")

            # 3. Quality Tag
            quality_tag = ptn.get("quality", "HD")

            # 4. Episode String (S01E01)
            s_tag = ""
            if ptn.get("season") and ptn.get("episode"):
                s_tag = f".S{ptn.get('season'):02d}-E{ptn.get('episode'):02d}"

            # 5. Construct Final Branded Name
            # Format: Title.S01E01.720p.[ShadowSystem].mp4
            branded_name = f"{safe_title}{s_tag}.{quality_tag}.{self.branding}{ext}"

            # Remove any double dots that might have occurred
            branded_name = branded_name.replace("..", ".")

            # 6. Perform Rename
            new_path = os.path.join(os.path.dirname(file_path), branded_name)
            try:
                os.rename(file_path, new_path)

                # Add the NEW path to cleanup targets so it gets deleted on cancel/finish
                cleanup_targets.append(new_path)

                file_path = new_path
                current_file_path = new_path  # Update the safety variable
                file_name = branded_name

                logger.info(f"🏷️ Branded via DB/TMDB as: {file_name}")
            except Exception as e:
                logger.error(f"Rename failed: {e}. Continuing with original.")

            # 3. Prepare Visuals
            clean_caption = formatter.build_caption(
                tmdb_id,
                meta,
                file_name,
                db_entry=db_item,
                episode_meta=ep_meta,  # <--- PASS THIS TO FORMATTER
            )
            buttons = formatter.build_buttons(db_item.get("short_id", ""))

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
                    if sample_path:
                        cleanup_targets.append(sample_path)

            # 5. Main Upload (With Fancy Caption)
            logger.info("🚀 Uploading Main Video...")
            self._last_log = -1
            self._last_terminal_pct = -1  # Reset for terminal

            video_msg = await self.client.send_document(
                chat_id=self.log_channel,
                document=file_path,
                file_name=file_name,
                caption=clean_caption,  # <--- The Professional Text
                reply_markup=buttons,
                force_document=True,
                progress=self.upload_progress,
            )

            # If task was cancelled, video_msg is None.
            if video_msg is None:
                logger.info(f"⚠️ Upload aborted for task {task_id}. Skipping indexing.")
                return False

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
                f"📸 <b>Gallery: {db_item.get('title')}</b>\n"
                f"🆔 TMDB: <code>{tmdb_id}</code>\n"
                f"📎 <a href='{msg_link}'>[Go to Main File]</a>"
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
                media_group.append(
                    InputMediaVideo(sample_path)
                )  # Add without caption first

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
                        reply_to_message_id=main_msg_id,  # Creates the thread logic
                    )

                    # Capture Data for Forwarding
                    msg_ids_to_forward = [m.id for m in album_msgs]

                    # Capture File IDs for DB (Screenshots only)
                    for m in album_msgs:
                        if m.photo:
                            screen_file_ids.append(m.photo.file_id)

                    # B: FORWARD TO BACKUP CHANNEL (Safety Copy)
                    # We forward the album we just sent
                    if self.backup_channel != 0 and msg_ids_to_forward:
                        await self.client.forward_messages(
                            chat_id=self.backup_channel,
                            from_chat_id=self.log_channel,
                            message_ids=msg_ids_to_forward,
                        )
                        logger.info(
                            f"🛡️ Album Mirrored ({len(msg_ids_to_forward)} parts)"
                        )

                except Exception as e:
                    logger.error(f"Asset/Album error: {e}")

            # 8. Database Indexing (Final Save)
            doc = video_msg.document
            decoded = FileId.decode(doc.file_id)

            ptn = PTN.parse(file_name)

            # --- STRUCTURE 1: The Raw File Data (All Media Types) ---
            db_file_entry = {
                "quality": ptn.get("quality", "720p"),
                "telegram_id": doc.file_id,  # Stores VIDEO id only
                "location_id": main_msg_id,  # Stores Message ID for Streaming headers
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                # Store detected season info here for flat filtering too
                "tg_raw": {
                    "media_id": decoded.media_id,
                    "access_hash": decoded.access_hash,
                    "file_reference": decoded.file_reference.hex(),
                },
                "subtitles": meta.get("subtitles", []),
                "audio_tracks": meta.get("audio", []),  # Maps from processor output
                "embeds": [],  # Populated by separate "Daisy Chain" job later
                "downloads": [],
                "added_at": int(time.time()),
            }

            # Normalize Mapping
            s_num, e_num, _ = await self.normalize_episode_mapping(
                int(tmdb_id), ptn, db_item.get("media_type", "movie"), file_name
            )

            # 1. Update the Main File List
            update_ops = {
                "$push": {"files": db_file_entry},
                "$set": {
                    "visuals.screenshots": screen_file_ids,
                    # Refresh Date so it bubbles to top of 'Recently Added'
                    "last_updated": int(time.time()),
                },
            }

            # Only index as Series if we have valid Episode Data
            if e_num is not None:
                # --- CASE A: ANIME ENHANCED OBJECT ---
                if db_item.get("media_type") == "anime":
                    ep_data = await self.meta_service.fetch_anime_episode_meta(
                        tmdb_id, e_num
                    )
                    ep_obj = {
                        "quality": ptn.get("quality", "720p"),
                        "episode": e_num,
                        "title": ep_data.get("name", f"Episode {e_num}"),
                        "title_japanese": ep_data.get("title_japanese"),
                        "title_romanji": ep_data.get("title_romanji"),
                        "aired": ep_data.get("aired"),
                        "score": ep_data.get("score"),
                        "filler": ep_data.get("filler", False),
                        "recap": ep_data.get("recap", False),
                        "synopsis": ep_data.get(
                            "synopsis"
                        ),  # MAL uses synopsis for episodes
                        "file_id": doc.file_id,
                        "unique_hash": decoded.media_id,
                    }
                # --- CASE B: TV STANDARD OBJECT ---
                else:
                    ep_data = await self.meta_service.fetch_show_episode_meta(
                        tmdb_id, s_num, e_num
                    )
                    ep_obj = {
                        "quality": ptn.get("quality", "720p"),
                        "episode": e_num,
                        "title": ep_data.get("name", f"Episode {e_num}"),
                        "overview": ep_data.get("overview"),
                        "runtime": ep_data.get("runtime"),
                        # Usage: https://image.tmdb.org/t/p/{size}/{still_path}
                        # Supported Sizes: w92, w154, w185, w342, w500, w780, original
                        # E.g., https://image.tmdb.org/t/p/original/s1ejjHUlB4S6SxkOkGmPQ7CfRgu.jpg
                        "still_path": ep_data.get("still_path"),
                        "file_id": doc.file_id,
                        # Useful for distinguishing "File X" from "File Y" in UI
                        "unique_hash": decoded.media_id,
                    }
                update_ops["$push"][f"seasons.{s_num}"] = ep_obj
                update_ops["$max"] = {"total_seasons": s_num}
                update_ops["$set"]["last_updated"] = int(time.time())

            await self.db.library.update_one(
                {"_id": db_item["_id"]}, update_ops, upsert=True
            )

            logger.info(
                f"✅ Index Complete for {db_item.get('title')} | ID: {db_item['_id']}"
            )

            if self.is_cancelled:
                logger.warning(
                    f"🚫 Suppression: Task {task_id} was cancelled, skipping success message."
                )
                return False

            # Final Redis Update
            if task_id and self.redis:
                await self.redis.hset(
                    f"task_status:{task_id}",
                    mapping={"status": "completed", "progress": 100},
                )
                await self.redis.expire(
                    f"task_status:{task_id}", 600
                )  # Keep for 10mins

            return True

        except (StopTransmission, Exception) as e:
            self.is_cancelled = True
            err_str = str(e)

            # 1. Handle Clean Aborts (User Cancelled)
            if (
                isinstance(e, StopTransmission)
                or "ABORTED_BY_SIGNAL" in err_str
                or "TASK_CANCELLED" in err_str
            ):
                logger.warning(f"🛑 Task {task_id} gracefully stopped.")
                if task_id and self.redis:
                    await self.redis.hset(
                        f"task_status:{task_id}", "status", "cancelled"
                    )

                # 📢 NOTIFY USER VIA THE ORIGIN CHAT
                target_chat = getattr(self, "notify_chat", self.log_channel)
                try:
                    await self.client.send_message(
                        chat_id=target_chat,  # <--- REDIRECTED
                        text=(
                            f"🛑 <b>Task Aborted</b>\n"
                            f"🆔 ID: <code>{task_id}</code>\n"
                            f"🗑️ Status: Content scrubbed and slot released."
                        ),
                    )
                except Exception as notify_err:
                    logger.error(f"Failed to send cancellation msg: {notify_err}")

            # 2. Catch & Silence the Pyrogram 'NoneType' write noise
            elif "'NoneType' object has no attribute 'write'" in err_str:
                logger.debug("Silenced Pyrogram session cleanup noise.")

            # 3. Handle Real Errors (Crashes/Network)
            else:
                logger.error(f"Critical Leech Fail: {e}")
                target_chat = getattr(self, "notify_chat", self.log_channel)
                try:
                    await self.client.send_message(
                        chat_id=target_chat,
                        text=f"❌ <b>Task Failed</b>\n🆔 ID: <code>{task_id or 'unknown'}</code>\nError: <code>{err_str[:50]}</code>",
                    )
                except:
                    pass

            return False
            logger.error(f"Critical Leech Fail: {e}")

        except Exception as e:
            # Catch the specific stop_transmission error string
            if (
                "unbound method stop_transmission" in str(e).lower()
                or "task_cancelled" in str(e).lower()
            ):
                logger.info(f"🛑 Upload {task_id} stopped via native signal.")
                # Update Redis
                if task_id and self.redis:
                    await self.redis.hset(
                        f"task_status:{task_id}", "status", "cancelled"
                    )

                # Send the "Aborted" message to origin (DM or Log)
                try:
                    await self.client.send_message(
                        chat_id=self.notify_chat,
                        text=f"🛑 <b>Task Aborted</b>\n🆔 ID: <code>{task_id}</code>",
                    )
                except:
                    pass
            else:
                # Real error handling...
                pass
            return False

        finally:
            # 9. Robust Cleanup

            # 1. DELETE THE TRIGGER COMMAND (The /leech message)
            if self.trigger_msg_id and self.notify_chat:
                try:
                    await self.client.delete_messages(
                        chat_id=(self.notify_chat), message_ids=int(self.trigger_msg_id)
                    )
                except:
                    pass

            # 2. SEND COMPLETION NOTIFICATION (Only if successful)
            # Note: 'msg_link' and 'db_item' are available from the try block scope if success
            if not self.is_cancelled and task_id:
                try:
                    # We fetch variables from local scope (safe if successful)
                    title = locals().get("db_item", {}).get("title", "Video")
                    link = locals().get("msg_link", "#")

                    await self.client.send_message(
                        chat_id=int(self.notify_chat),
                        text=(
                            f"✅ <b>Task Complete</b>\n"
                            f"📦 <code>{branded_name}</code>\n"
                            f"👤 {self.current_user_tag}\n"
                            f"📎 <a href='{link}'>[View in Log]</a>"
                        ),
                        disable_web_page_preview=True,
                    )
                except:
                    pass

            # 3. MASTER REGISTRY PURGE
            if task_id:
                async with task_dict_lock:
                    task_dict.pop(task_id, None)

            # 4. RELEASE USER SLOT
            if task_id and user_id != "0" and self.redis:
                limit_key = f"active_user_tasks:{user_id}"
                await self.redis.srem(limit_key, task_id)
                logger.info(f"🔓 Slot released for User {user_id}")

            # 5. Cleanup temporary files
            # Master List: Init path + Current path + Screenshots
            targets = set(cleanup_targets)
            if "current_file_path" in locals():
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
                        logger.error(
                            f"❌ Failed to delete {os.path.basename(abs_path)}: {e}"
                        )

            logger.info("✅ Cleanup phase done.")
