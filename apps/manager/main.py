from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from services.database import db_service
from services.bot_manager import bot_manager
from routers import library  # Added this
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

# --- ROUTES ---
app.include_router(library.router)  # Wired the Library Router

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
