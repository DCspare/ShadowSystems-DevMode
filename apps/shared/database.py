# apps/shared/database.py 
import logging
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorClient

# 🔄 CHANGE: Import from local settings, not core.config
from shared.settings import settings

logger = logging.getLogger("SharedDB")

class ShadowDatabase:
    """
    Shared Persistence Service
    Accessible by Manager (Brain) and Worker (Muscle).
    Connects to external Cloud DBs (Atlas/Upstash)
    """
    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.redis = None

    async def connect(self):
        """Initializes connection pools using Shared Settings"""
        try:
            # 1. MongoDB Connection
            self.mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
            
            # Use default db from URI or fallback to 'shadow_systems'
            try:
                self.db = self.mongo_client.get_default_database()
            except Exception:
                # Fallback if URI doesn't have a /db-name
                self.db = self.mongo_client["shadow_systems"]
            
            # Health Check
            # (Note: Some environments might restrict admin ping, but fine for now)
            await self.mongo_client.admin.command('ping') 
            logger.info(f"Successfully connected to MongoDB Atlas. Using DB: {self.db.name}")

            # 2. Redis Connection (Upstash)
            self.redis = Redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_timeout=5
            )
            await self.redis.ping()
            logger.info("✅ Redis Connected")

        except Exception as e:
            logger.error(f"❌ DB Connection Fail: {e}")
            raise

# Singleton instance exported to all apps
db_service = ShadowDatabase()
