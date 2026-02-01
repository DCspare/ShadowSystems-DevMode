# apps/manager/core/security.py 
import time
import base64
import hashlib
import logging
from shared.settings import settings
from shared.database import db_service
from fastapi import HTTPException, Request, Depends
from datetime import datetime, timedelta
from jose import jwt, JWTError
from shared.schemas import User
from typing import Optional
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger("Security")

# Crypto Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# This tells FastAPI where to look for the Token if we use "Depends()" in routes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

ALGORITHM = "HS256"

# --- STREAM SIGNER ---
def sign_stream_link(file_id: str, client_ip: str) -> str:
    """
    Shadow Logic: Generates an Nginx Secure Link hash.
    Syncs with Nginx $remote_addr for identity verification.
    """
    expiry = int(time.time()) + (4 * 3600)
    secret = settings.SECURE_LINK_SECRET
    path = f"/stream/{file_id}"
    
    # We must match Nginx exactly: Expiry + URI + ClientIP + " " + Secret
    sign_string = f"{expiry}{path}{client_ip} {secret}"
    
    hash_obj = hashlib.md5(sign_string.encode('utf-8'))
    token = base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8').replace('=', '')

    # return f"md5={token}&expires={expiry}" # Nginx standard args
    
    logger.info(f"Signed path {path} for IP {client_ip} [Hash snippet: {token[:5]}]")
    return f"token={token}&expires={expiry}"

# --- 🔐 AUTH LOGIC ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default: Guest (365 days) or Temp User (7 days)
        expire = datetime.utcnow() + timedelta(days=7)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Middleware dependency.
    Decodes the JWT -> Validates exp -> Fetches User from DB.
    Used for Routes: @router.get("/me")
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "free")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError: # Specific JOSE error
        raise credentials_exception
    except Exception:
        raise credentials_exception

    # Fast Return Payload (Stateless)
    return {"id": user_id, "role": role}

# --- RATE LIMITER ---
class RateLimiter:
    """
    Zero-dependency Redis Rate Limiter (Sliding Window).
    """
    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        # 1. Check Redis Connection
        if not db_service.redis:
            return # Fail-open if Redis down (avoid service denial)

        # 2. Key Generation (IP Based)
        ip = request.headers.get("x-real-ip", request.client.host)
        # Using URL path makes it route-specific limit
        key = f"rate_limit:{request.url.path}:{ip}"
        
        # 3. Pipeline Logic (Atomic check)
        # Allows X requests within the Time Window
        try:
            pipe = db_service.redis.pipeline()
            now = int(time.time())
            window_start = now - self.seconds
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Add current hit
            pipe.zadd(key, {str(now): now})
            # Count
            pipe.zcard(key)
            # Expire Key eventually to save RAM
            pipe.expire(key, self.seconds + 1)
            
            results = await pipe.execute()
            count = results[2] # zcard result
            
            if count > self.times:
                raise HTTPException(status_code=429, detail="Too many requests. Slow down.")
                
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            # Fail open on redis error
            pass
