from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from services.database import db_service
from services.bot_manager import bot_manager # New import
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Manager")

app = FastAPI(title="Shadow Systems Manager", version="2.0.0")

# --- MIDDLEWARE ---
if settings.MODE == "DEV":
    allow_origins = ["*"]
else:
    allow_origins = [f"https://{settings.DOMAIN_NAME}"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Ignition Sequence: Database then Bot"""
    logger.info(f"Initializing Shadow Brain in {settings.MODE} mode...")
    
    # 1. Initialize Database
    try:
        await db_service.connect()
    except Exception as e:
        logger.error(f"DATABASE CRITICAL: Bot will start in Offline Mode. Error: {e}")

    # 2. Initialize Manager Bot (Bot Identity)
    try:
        await bot_manager.start()
    except Exception as e:
        logger.error(f"TELEGRAM CRITICAL: Failed to start Bot Service: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup Sequence"""
    await bot_manager.stop()
    logger.info("Shadow Brain deactivated.")

@app.get("/health")
async def health_check():
    return {"status": "online", "db": "connected" if db_service.db is not None else "failed"}