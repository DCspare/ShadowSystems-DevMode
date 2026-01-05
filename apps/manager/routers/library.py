from fastapi import APIRouter, HTTPException
from services.metadata import metadata_service
from services.database import db_service
from core.utils import generate_short_id
import logging

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
async def list_indexed():
    """Return all items stored in our MongoDB Library"""
    cursor = db_service.db.library.find({})
    items = await cursor.to_list(length=100)
    for i in items:
        i["_id"] = str(i["_id"])
    return {"library": items}

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
