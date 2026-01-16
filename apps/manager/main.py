import logging
from routers import library 
from core.config import settings
from fastapi import FastAPI, Request 
from services.database import db_service
from fastapi.responses import JSONResponse
from services.bot_manager import bot_manager
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Manager")

class GatekeeperMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. WHITE-LIST ROUTES (Always Open)
        # /health = Monitoring, /docs = Swagger, /library/internal = Nginx Resolver
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"] or \
           request.url.path.startswith("/library/internal") or \
           request.method == "OPTIONS": # Allow Preflight
            return await call_next(request)

        # 2. DEV MODE BYPASS
        if settings.MODE == "DEV":
            # Pass, but we can log suspicious traffic here if wanted
            return await call_next(request)

        # 3. PRODUCTION ENFORCEMENT
        # Verify Origin Logic (If STRICT) or Secret Logic
        
        # Strategy: Strict Secret Check
        client_key = request.headers.get("X-Shadow-Secret")
        
        # NOTE: For Public GET routes (like SEO Metadata), you might want to skip this 
        # so GoogleBot can crawl. Uncomment next line to Lock Writes ONLY:
        # if request.method in ["GET"]: return await call_next(request)
        
        if client_key != settings.API_SECRET_KEY:
            logger.warning(f"⛔ Intruder Blocked: {request.client.host}")
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
    allow_origins = [f"https://{settings.DOMAIN_NAME}"]

app = FastAPI(title="Shadow Systems Manager", version="2.0.0")

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

# --- LIFECYCLE EVENTS ---
@app.on_event("startup")
async def startup_event():
    """Ignition Sequence"""
    logger.info(f"Initializing Shadow Brain in {settings.MODE} mode...")
    
    # Initialize Database
    try:
        await db_service.connect()
    except Exception as e:
        logger.error(f"DATABASE CRITICAL: {e}")

    # Initialize Manager Bot
    try:
        await bot_manager.start()
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
