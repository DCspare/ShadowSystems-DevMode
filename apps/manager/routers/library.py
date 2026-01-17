# apps/manager/routers/library.py 
import os
import sys
import base64
import logging
sys.path.append("/app")
from fastapi import Depends
from pyrogram.file_id import FileId # Used to decode the string identity
from shared.schemas import SignRequest
from services.database import db_service
from core.utils import generate_short_id
from core.security import sign_stream_link 
from fastapi.responses import JSONResponse
from services.bot_manager import bot_manager
from services.metadata import metadata_service
from fastapi import APIRouter, HTTPException , Request
from core.security import sign_stream_link, RateLimiter

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
