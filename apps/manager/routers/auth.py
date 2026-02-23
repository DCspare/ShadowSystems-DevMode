# apps/mmanager/routers/auth.py 
import sys
import uuid
import logging
import time
sys.path.append("/app/shared")
from fastapi import APIRouter, Request, HTTPException, Response, Depends
from shared.database import db_service
from core.security import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("Auth")

@router.post("/guest")
async def register_guest(response: Response, request: Request):
    """
    Generate a tracked 'Guest' identity. 
    Frontend calls this on first load if no cookie exists.
    """
    # 1. Create Identity
    guest_uuid = str(uuid.uuid4())[:12]
    unique_id = f"guest_{guest_uuid}"
    
    client_ip = request.headers.get("x-real-ip", request.client.host)
    user_agent = request.headers.get("user-agent", "unknown")

    # 2. Persist in DB (To track watch history)
    user_doc = {
        "id": unique_id,
        "type": "guest",
        "role": "free",
        "created_at": int(time.time()),
        "meta": { "ip_seed": client_ip, "ua": user_agent },
        "history": {}
    }
    
    await db_service.db.users.insert_one(user_doc)
    
    # 3. Mint JWT
    access_token = create_access_token(
        data={"sub": unique_id, "role": "free"}
    )
    
    # 4. Set HttpOnly Cookie (Security Best Practice)
    response.set_cookie(
        key="shadow_session",
        value=access_token,
        httponly=True,
        max_age=2592000, # 30 Days
        samesite="lax",
        secure=True # Only works on HTTPS (PROD)
    )
    
    return {"status": "registered", "user_id": unique_id, "role": "guest"}

@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    """
    Returns profile. Used by Frontend to restore state on reload.
    """
    if not user:
        return {"authenticated": False}
        
    # Fetch full history/settings from DB
    db_user = await db_service.db.users.find_one({"id": user["id"]})
    
    if not db_user:
        # Edge case: Token valid but DB deleted? Force logout logic in frontend
        return {"authenticated": False, "error": "user_not_found"}
    
    # Sanitize sensitive internal fields if any
    db_user.pop("_id", None) 
    
    return {"authenticated": True, "user": db_user}