import logging
from fastapi import APIRouter, HTTPException
from services.metadata import metadata_service
from services.database import db_service
from core.utils import generate_short_id
from core.security import sign_stream_link 
from fastapi import Request

logger = logging.getLogger("Library")
router = APIRouter(prefix="/library", tags=["Library"])

@router.get("/search")
async def search_online(q: str, type: str = "movie"):
    """Search for titles live on TMDB"""
    try:
        results = await metadata_service.search_tmdb(q, type)
        return {"results": results}
    except Exception as e:
        logger.error(f"Search failure: {e}")
        return {"results": [], "error": str(e)}

@router.get("/list")
async def list_library():
    cursor = db_service.db.library.find({})
    items = await cursor.to_list(length=100)
    for i in items:
        i["_id"] = str(i["_id"])
    return {"library": items}

@router.get("/view/{short_id}")
async def get_by_slug(short_id: str, request: Request):
    """
    Shadow Logic: Returns metadata with signed 'VIP' links.
    """
    item = await db_service.db.library.find_one({"short_id": short_id})
    if not item:
        raise HTTPException(status_code=404, detail="Title not found")
    
    # 🔍 SHADOW FIX: Use the IP sent by the Gateway proxy
    client_ip = request.headers.get("x-real-ip", request.client.host)
    
    logger.info(f"Generating links for ShortID: {short_id} (Client IP: {client_ip})") 
    
    # Process files to add signatures
    if "files" in item:
        for file in item["files"]:
            # Generate the token based on TG ID and Client IP
            signature_query = sign_stream_link(file["telegram_id"], client_ip)
            # The URL will look like: /api/stream/TELEGRAM_ID?token=HASH&expires=TIMESTAMP
            file["stream_url"] = f"/stream/{file['telegram_id']}?{signature_query}"
    
    item["_id"] = str(item["_id"])
    return item

@router.post("/index/{media_type}/{tmdb_id}")
async def index_content(media_type: str, tmdb_id: int):
    """Save content metadata to MongoDB"""
    try:
        # Check duplication
        existing = await db_service.db.library.find_one({"tmdb_id": tmdb_id})
        if existing:
            return {"status": "already_indexed", "short_id": existing["short_id"]}

        # Fetch Deep Metadata
        details = await metadata_service.get_details(tmdb_id, media_type)
        if not details:
            raise HTTPException(status_code=404, detail="TMDB returned no data")

        # Create Schema (context_04 aligned)
        doc = {
            "tmdb_id": tmdb_id,
            "short_id": generate_short_id(),
            "media_type": media_type,
            "title": details.get("title") or details.get("name") or "Unknown Title",
            "year": (details.get("release_date") or details.get("first_air_date") or "0000")[:4],
            "genres": [g["name"] for g in details.get("genres", [])],
            "rating": details.get("vote_average", 0),
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
