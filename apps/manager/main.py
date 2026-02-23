# apps/manager/main.py
import sys
import logging
import asyncio
sys.path.append("/app/shared") # Docker fix for imports 
from routers import library, auth, admin
from fastapi import FastAPI, Request 
from shared.settings import settings
from shared.tg_client import TgClient
from shared.database import db_service
from fastapi.responses import JSONResponse
from services.bot_manager import bot_manager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Manager")

class GatekeeperMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # path IS DEFINED GLOBALLLY 
        path = request.url.path

        # 1. WHITE-LIST ROUTES (Always Open)
        # /health = Monitoring, /docs = Swagger, /library/internal = Nginx Resolver
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"] or \
           request.url.path.startswith("/library/internal") or \
           request.method == "OPTIONS": # Allow Preflight
            return await call_next(request)

        # 2. DEV MODE BYPASS (Write Operations)
        if settings.MODE == "DEV":
            # Pass, but we can log suspicious traffic here if wanted
            return await call_next(request)

        # 3. PUBLIC READ ACCESS (SEO / Guest Friendly)
        # Allow anyone to View List, Search, and View Items
        if request.method == "GET" and not path.startswith("/admin") and not path.startswith("/library/internal"):
            return await call_next(request)

        # 4. INTERNAL & SYSTEM PROTECTION (Always locked)
        # Nginx uses this, or Manual Admin checks
        if path.startswith("/library/internal"):
             # We rely on Nginx IP whitelisting or Internal docker network
             # If accessed publicly, we can enforce secret, but usually Nginx blocks external access to this path anyway.
             # For now, let's allow it if it's within the Docker network (hard to detect here easily) 
             # OR strictly check secret if you want:
             pass

        # 5. STRICT PROD AUTHENTICATION (For Writes / Admin / Sensitive)
        client_key = request.headers.get("X-Shadow-Secret")
        
        if client_key != settings.API_SECRET_KEY:
            logger.warning(f"⛔ Intruder Blocked: {request.client.host} {request.method} {path}")
            return JSONResponse(
                status_code=403, 
                content={"detail": "🛡️ Access Denied: Missing Shadow-Key"}
            )

        return await call_next(request)

# --- APP INITIALIZATION ---

app = FastAPI(title="Shadow Systems Manager", version="2.0.0")

# --- 1. Register Gatekeeper (Security Layer First) ---
app.add_middleware(GatekeeperMiddleware)

# --- 2. Register CORS (Browser Access Layer) ---
if settings.MODE == "DEV":
    allow_origins = ["*"]
else:
    # Use format: ["https://shadow-systems.xyz"]
    allow_origins = [f"https://{settings.DOMAIN_NAME}"]

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
app.include_router(library.router)  
app.include_router(auth.router)
app.include_router(admin.router)

# --- LIFECYCLE EVENTS ---
@app.on_event("startup")
async def startup_event():
    """Ignition Sequence"""
    logger.info(f"Initializing Shadow Brain in {settings.MODE} mode...")
    
    # Initialize Database
    try:
        await db_service.connect()
        logger.info("Shadow Database connected.")

    except Exception as e:
        logger.error(f"DATABASE CRITICAL: {e}")

    # Initialize Manager Bot
    try:
        await bot_manager.start() 
        logger.info("Manager connected.")

    except Exception as e:
        logger.error(f"TELEGRAM CRITICAL: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup Sequence"""
    await bot_manager.stop()
    logger.info("Shadow Brain deactivated.")

@app.get("/health")
async def health_check():
    return {"status": "online", "db": "connected" if db_service.db is not None else "failed"}

# Redirect root for browser diagnostics
@app.get("/")
async def root():
    return {"message": "Shadow Manager API Level 2026 active"}
