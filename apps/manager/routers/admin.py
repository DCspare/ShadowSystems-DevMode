# apps/manager/routers/admin.py
import sys
sys.path.append("/app/shared")
from fastapi import APIRouter, HTTPException, Depends
from shared.database import db_service
from typing import Optional

# Requires Gatekeeper Middleware (X-Shadow-Secret check) from main.py
router = APIRouter(prefix="/admin", tags=["Admin Operations"])

@router.get("/users")
async def list_users(skip: int = 0, limit: int = 50, role: Optional[str] = None):
    """
    User Directory for Admin Panel.
    Query: /admin/users?role=guest&limit=100
    """
    query = {}
    if role:
        query["role"] = role

    # Count total for pagination UI
    total = await db_service.db.users.count_documents(query)
    
    # Sort by Newest First
    cursor = db_service.db.users.find(query).sort("created_at", -1).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)

    # Sanitize _id for JSON output
    for u in users:
        u["_id"] = str(u["_id"])

    return {
        "count": len(users), 
        "total": total, 
        "data": users
    }

@router.get("/stats")
async def system_health():
    """
    Dashboard Live Metrics (Redis/Mongo)
    """
    try:
        # Check active leech tasks
        queue_len = await db_service.redis.llen("queue:leech")
        
        # Simple counts
        docs_users = await db_service.db.users.count_documents({})
        docs_movies = await db_service.db.library.count_documents({"media_type": "movie"})
        
        return {
            "status": "online",
            "active_tasks": queue_len,
            "metrics": {
                "total_users": docs_users,
                "library_size": docs_movies
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))