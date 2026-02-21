# apps/shared/settings.py 
import os
from pydantic import Field
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """
    SINGLE SOURCE OF TRUTH (Production Configuration)
    
    This validates your .env file on startup. 
    If a required variable is missing, the App/Worker will CRASH immediately 
    (Fail Fast principle), preventing silent errors later.
    """

    # ==========================================
    # 🌍 ENVIRONMENT CONTEXT
    # ==========================================
    MODE: str = "PROD"  # Options: "DEV" (Debug on) or "PROD" (Secure)
    DOMAIN_NAME: str = "shadow-systems.xyz" # Used for Magic Links & Redirects

    # ==========================================
    # 🗝️ TELEGRAM IDENTITY (The Keys)
    # ==========================================
    # Application credentials from my.telegram.org
    TG_API_ID: int 
    TG_API_HASH: str
    
    # Bots (Tokens from @BotFather)
    TG_BOT_TOKEN: str       # For Manager (Admin Interface)
    TG_WORKER_BOT_TOKEN: str # For Worker (in Safe Mode)
    TG_STREAM_BOT_TOKEN: str # For Stream Engine (Generic)
    
    # User Identity (MTProto High Speed)
    # This string allows us to clone the Worker session without OTP
    TG_SESSION_STRING: Optional[str] = None
    
    # Super Admin (YOU) - Bypass all checks
    TG_OWNER_ID: int 

    # ==========================================
    # 📡 CHANNEL MAPPING (The Warehouse)
    # ==========================================
    # Target IDs (integers, usually -100...)
    TG_LOG_CHANNEL_ID: int
    TG_BACKUP_CHANNEL_ID: int = 0  # 0 = Disabled
    TG_DUMP_CHANNEL_ID: int = 0
    TG_UPDATE_CHANNEL_ID: int = 0

    # ==========================================
    # 💾 DATABASES (Persistence)
    # ==========================================
    MONGO_URL: str # Atlas Connection String
    REDIS_URL: str # Upstash/Redis Connection String

    # ==========================================
    # 🔒 SECURITY & ENCRYPTION
    # ==========================================
    # Generates user auth tokens
    JWT_SECRET: str
    # Used by Nginx to verify stream links
    SECURE_LINK_SECRET: str
    # API Handshake Header (Backend <-> Frontend)
    # Must match "X-Shadow-Secret" header
    API_SECRET_KEY: str = "unsafe_default" 

    # ==========================================
    # 🔌 FEATURE FLAGS (Toggles)
    # ==========================================
    # If True: Worker generates 30s sample. False: Save CPU.
    GENERATE_SAMPLES: bool = True 
    
    # Branding String for filenames (e.g. "[ShadowSystems]")
    FILE_BRANDING_TAG: str = "[ShadowSystem]"
    
    # ==========================================
    # 🛡️ QUEUE & LIMITS (Shadow-MLB)
    # ==========================================
    ENABLE_USER_LIMITS: bool = False # set True for public launch
    MAX_TASKS_PER_USER: int = 3
    MAX_TOTAL_TASKS: int = 10
    STATUS_UPDATE_INTERVAL: int = 6 # Seconds

    # --- HANDSHAKE & PERSISTENCE ---
    # Default is True for Cloud IDEs (Dev), set to False in Production for .session files
    USE_IN_MEMORY_SESSION: bool = True  

    # Swarm/Handshake config (From WZML logic)
    HELPER_TOKENS: Optional[str] = None # Format: "token1 token2 token3"
    DOWNLOAD_DIR: str = "/app/downloads"
    
    # Mirror specific logic
    IS_PREMIUM_USER: bool = False
    MAX_SPLIT_SIZE: int = 2097152000 # 2GB

    # ==========================================
    # 🎥 3RD PARTY INTEGRATIONS
    # ==========================================
    # Metadata Source (TheMovieDB v3 API Key)
    TMDB_API_KEY: str
    
    # Monetization (Ads)
    ADSTERRA_PID: Optional[str] = None
    SHORTENER_API_TOKEN: Optional[str] = None

    # ==========================================
    # 🔗 MIRROR / DAISY-CHAIN KEYS
    # ==========================================
    PIXELDRAIN_API_KEY: Optional[str] = None
    VIDHIDE_API_KEY: Optional[str] = None
    
    # ==========================================
    # 🛠️ CONFIG LOADERS
    # ==========================================
    model_config = SettingsConfigDict(
        # Look for .env in Root or Apps folder
        # 'ignore' means: If .env has extra keys (trash), don't crash.
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore", 
        case_sensitive=True 
    )

# Create singleton instance
settings = AppSettings()