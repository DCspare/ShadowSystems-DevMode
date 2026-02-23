# apps/manager/routers/library.py 
import os
import sys
import base64
import logging
import subprocess 
sys.path.append("/app")
from fastapi import Depends
from pyrogram.file_id import FileId # Used to decode the string identity
from shared.schemas import SignRequest
from shared.settings import settings
from shared.database import db_service
from shared.utils import generate_short_id
from core.security import sign_stream_link 
from services.bot_manager import bot_manager
from services.metadata import metadata_service
from fastapi import APIRouter, HTTPException , Request
from core.security import sign_stream_link, RateLimiter
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("Library")
# Router handles the /library prefix internally
router = APIRouter(prefix="/library", tags=["Library"])

# --- 1. INTERNAL (Nginx Resolver) ---
@router.get("/internal/stream_meta/{telegram_id:path}")
async def internal_resolver(telegram_id: str):
    """
    Called by Nginx auth_request.
    Maps a Telegram ID -> MsgID + ChatID & Location ID for the Go Engine.
    """
    try:
        clean_id = telegram_id.split('?')[0]
        # Query specifically inside the files array
        db_item = await db_service.db.library.find_one(
            {"files.telegram_id": clean_id}, {"files.$": 1}
        )
        if not db_item: 
            # Fallback: Maybe the client passed a raw short_id/stream string logic
            raise HTTPException(status_code=404)

        file_rec = db_item["files"][0]

        headers = {
            "X-Location-Msg-ID": str(file_rec.get("location_id", "")),
            "X-Location-Chat-ID": os.getenv("TG_LOG_CHANNEL_ID")
        }
        return JSONResponse(content={"status": "ok"}, headers=headers)
    except Exception:
        raise HTTPException(status_code=400)


# --- 2. PUBLIC/FRONTEND ROUTES ---

@router.get("/search")
async def search_online(q: str, type: str = "multi"):
    """
    Search TMDB.
    Usage: /search?q=Monster&type=tv (for Anime/Shows)
           /search?q=Avatar&type=movie
           /search?q=One+Piece&type=multi (Search all)
    """
    try:
        results = await metadata_service.search_tmdb(q, type)
        return {"results": results}
    except Exception as e:
        logger.error(f"Search failure: {e}")
        return {"results": [], "error": str(e)}

@router.get("/list")
async def list_library(skip: int = 0, limit: int = 100):
    """Manifest fetcher with pagination."""
    cursor = db_service.db.library.find({}).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    for i in items: i["_id"] = str(i["_id"])
    return {"count": len(items), "library": items}

@router.get("/view/{short_id}")
async def get_by_slug(short_id: str, request: Request):
    """
    Returns full metadata for a specific Movie/Show.
    Generates Signed Streaming Links on the fly for the IP.
    """
    item = await db_service.db.library.find_one({"short_id": short_id})
    if not item: raise HTTPException(status_code=404)

    client_ip = request.headers.get("x-real-ip", request.client.host)

    # if "files" in item:
    #     for file in item["files"]:
    #         sig = sign_stream_link(file["telegram_id"], client_ip)
    #         file["stream_url"] = f"/stream/{file['telegram_id']}?{sig}"

    item["_id"] = str(item["_id"])
    return item

# --- 3. ADMIN MANAGEMENT ROUTES ---

@router.post("/index/{media_type}/{tmdb_id}")
async def index_content(media_type: str, tmdb_id: int):
    """
    MANUAL INGEST: Force-Add metadata to DB.
    Use this to 'Start' a movie entry before leeching.
    """
    try:
        # Check existing
        existing = await db_service.db.library.find_one({"tmdb_id": tmdb_id})
        if existing:
            return {"status": "already_indexed", "short_id": existing["short_id"],
            "_id": str(existing["_id"])}

        # Fetch Deep Metadata
        details = await metadata_service.get_details(tmdb_id, media_type)
        if not details:
            raise HTTPException(status_code=404, detail="TMDB ID invalid")

        # Create Schema (context_04 aligned)
        doc = {
            "tmdb_id": tmdb_id,
            "short_id": generate_short_id(),
            "media_type": media_type,
            "title": details.get("title") or details.get("name") or "Unknown Title",
            "clean_title": details.get("title") or details.get("name") or "Unknown Title",
            "year": (details.get("release_date") or details.get("first_air_date") or "0000")[:4],
            "release_date": details.get("release_date") or details.get("first_air_date"), # Needed for Fallbacks
            "genres": [g["name"] for g in details.get("genres", [])],
            "vote_average": details.get("vote_average", 0), 
            "rating": details.get("vote_average", 0), # Legacy alias
            "overview": details.get("overview", "No synopsis available."),
            "status": "available",
            "visuals": {
                "poster": f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}" if details.get('poster_path') else None,
                "backdrop": f"https://image.tmdb.org/t/p/original{details.get('backdrop_path')}" if details.get('backdrop_path') else None
            },
            "files": [] 
        }

        await db_service.db.library.insert_one(doc)
        logger.info(f"Indexed: {doc['title']} as {doc['short_id']}")
        
        # Format response
        doc["_id"] = str(doc["_id"])
        return {"status": "success", "data": doc}
        
    except Exception as e:
        logger.error(f"Indexing error for TMDB {tmdb_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sign", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def sign_video_url(payload: SignRequest, request: Request):
    """
    Lazy Signer: Generates Nginx Secure Link on demand.
    Input: { "short_id": "v7K...", "file_id": "BQAC..." }
    """
    # 1. Validate File Existence
    # Security: Ensure this file actually belongs to the content associated with short_id
    item = await db_service.db.library.find_one(
        { "short_id": payload.short_id, "files.telegram_id": payload.file_id }
    )
    if not item: raise HTTPException(404, "Invalid file for this content")

    # 2. Capture Real IP
    client_ip = request.headers.get("x-real-ip", request.client.host)
    
    # 3. Generate
    sig = sign_stream_link(payload.file_id, client_ip)
    
    return {
        "status": "signed",
        "stream_url": f"/stream/{payload.file_id}?{sig}",
        "expires_in": 14400 # 4 Hours
    }

@router.delete("/delete/{tmdb_id}")
async def delete_content(tmdb_id: int):
    """
    NUKES a movie from the database. 
    Does NOT delete files from Telegram (Safety).
    """
    res = await db_service.db.library.delete_one({"tmdb_id": tmdb_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Item not found in Library")
    
    logger.info(f"🗑️ Deleted Library Entry: {tmdb_id}")
    return {"status": "deleted", "id": tmdb_id}

@router.patch("/update/{tmdb_id}")
async def update_metadata(tmdb_id: int, payload: dict):
    """
    Manual override for titles/posters/year.
    Body example: { "title": "New Name", "year": "2025" }
    """
    if not payload: raise HTTPException(400, "Empty payload")
    
    # Sanitize: prevent changing _id or tmdb_id directly here if strict
    # Simple sanitization
    allowed = ["title", "year", "rating", "status", "short_id", "visuals"]
    safe_updates = {k: v for k, v in payload.items() if k in allowed}
    
    if "visuals" in payload:
        # Dot notation for deep updates would be better, but simple set for now
        safe_updates["visuals"] = payload["visuals"]

    res = await db_service.db.library.update_one(
        {"tmdb_id": tmdb_id},
        {"$set": safe_updates}
    )
    
    if res.matched_count == 0: raise HTTPException(404, "Not found")
    
    return {"status": "updated", "modifications": res.modified_count}

@router.delete("/remove_file/{tmdb_id}")
async def remove_specific_file(tmdb_id: int, file_id: str, season: int = 0):
    """
    Precision Strike: Removes a SINGLE file link without deleting the movie meta.
    - If season=0 (default): Targets 'files' array (Movies).
    - If season=N (series): Targets 'seasons.N' array.
    """
    try:
        # Case A: Movie (files array uses 'telegram_id' key)
        if season == 0:
            query_update = {
                "$pull": { "files": { "telegram_id": file_id } } 
            }
        # Case B: Series (seasons.X list uses 'file_id' key in schema)
        else:
            # Dynamically target the specific season key (e.g., "seasons.1")
            target_key = f"seasons.{season}"
            query_update = {
                "$pull": { target_key: { "file_id": file_id } }
            }

        result = await db_service.db.library.update_one(
            {"tmdb_id": tmdb_id},
            query_update
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="File ID not found or content does not exist")

        logger.info(f"✂️ Granular Delete: Removed {file_id} from TMDB:{tmdb_id} (S{season})")
        return {"status": "removed", "tmdb_id": tmdb_id, "removed_file": file_id}

    except Exception as e:
        logger.error(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@router.post("/attach_file/{tmdb_id}")
async def attach_media_manually(tmdb_id: int, file_path: str):
    """
    Shadow Logic: Triggers the Worker to process a local file 
    and link it to a movie. (Bridge Step for Phase 3).
    """
    # For now, we use a simple Redis message to signal the Worker
    # Payload: tmdb_id|file_path
    payload = f"{tmdb_id}|{file_path}"
    await db_service.redis.lpush("queue:leech", payload)
    return {"status": "task_queued", "tmdb_id": tmdb_id, "file": file_path}

# --- On-The-Fly Subtitle Extractor ---
@router.get("/subtitle/{file_id}/{index}.vtt")
async def get_subtitle(file_id: str, index: int):
    """
    On-the-fly Subtitle Extractor.
    Extracts track {index} from the Telegram stream and converts to VTT.
    """
    # 1. Lookup Location Metadata (Same logic as Nginx resolver)
    db_item = await db_service.db.library.find_one(
        {"files.telegram_id": file_id}, {"files.$": 1}
    )
    if not db_item:
        raise HTTPException(status_code=404, detail="File not found in DB")

    file_rec = db_item["files"][0]
    msg_id = file_rec.get("location_id")
    chat_id = settings.TG_LOG_CHANNEL_ID # From shared settings

    # 2. Build the Internal Stream URL (Pointing to our Go Engine)
    # We use the internal docker name 'gateway' or 'stream-engine'
    # We bypass Secure Link check here because it's an internal server-to-server call
    source_url = f"http://stream-engine:8000/stream/{file_id}"

    # 3. FFmpeg Command with injected Header
    # We use '-headers' to pass the X-Location info to Go via FFmpeg's HTTP client
    # -i: source | -map 0:s:{index}: extract specific sub | -f webvtt: output format | -: pipe to stdout
    headers = f"X-Location-Msg-ID: {msg_id}\r\nX-Location-Chat-ID: {chat_id}\r\n"

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", 
        "error",
        "-headers", headers, 
        "-analyzeduration", "10000000", 
        "-probesize", "10000000",
        "-i", source_url,
        "-map", f"0:{index}", 
        "-f", "webvtt", "-"
    ]

    try:
        # We use a context manager to ensure the process is killed if the request is closed
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            bufsize=10**6 # 1MB Buffer
        )
        
        # We stream the response directly to the browser
        def generate():
            try:
                # Stream the output
                for line in iter(process.stdout.readline, b""):
                    yield line
            finally:
                # Cleanup
                process.stdout.close()
                process.stderr.close()
                process.terminate()

        return StreamingResponse(generate(), 
        media_type="text/vtt")

    except Exception as e:
        logger.error(f"💥 Subtitle Engine Crashed: {e}")
        raise HTTPException(status_code=500, detail="Could not extract subtitle")