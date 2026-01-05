from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from core.config import settings
import logging

logger = logging.getLogger("Database")

class ShadowDatabase:
    """
    Persistence Service
    Connects to external Cloud DBs (Atlas/Upstash)
    """
    def __init__(self):
        self.mongo_client = None
        self.db = None
        self.redis = None

    async def connect(self):
        """Initializes connection pools"""
        try:
            # 1. MongoDB Connection
            self.mongo_client = AsyncIOMotorClient(settings.MONGO_URL)
            
            # Use default db from URI or fallback to 'shadow_systems'
            try:
                self.db = self.mongo_client.get_default_database()
            except Exception:
                # Fallback if URI doesn't have a /db-name
                self.db = self.mongo_client["shadow_systems"]
            
            # Health check: Ping the admin database
            await self.mongo_client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB Atlas. Using DB: {self.db.name}")

            # 2. Redis Connection (Upstash)
            self.redis = Redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_timeout=5
            )
            await self.redis.ping()
            logger.info("Successfully connected to Upstash Redis.")

        except Exception as e:
            logger.error(f"Failed to connect to databases: {e}")
            raise

# Singleton instance
db_service = ShadowDatabase()