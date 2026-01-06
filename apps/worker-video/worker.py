import asyncio
import logging
import os
from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VideoWorker")

class VideoWorker:
    def __init__(self):
        self.app = None
        self.db = None
        self.redis = None
        self.worker_id = os.getenv("WORKER_ID", "video_worker_1")

    async def init_services(self):
        """Link to Cloud Persistence & Telegram Swarm"""
        logger.info(f"Initializing Worker {self.worker_id}...")
        
        # 1. MongoDB Connection (Static database name for absolute reliability)
        mongo_url = os.getenv("MONGO_URL")
        mongo_client = AsyncIOMotorClient(mongo_url)
        self.db = mongo_client["shadow_systems"] # Manual database selection
        
        # 2. Redis Connection
        self.redis = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        
        # 3. Identity Verification
        bot_token = os.getenv("TG_WORKER_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TG_WORKER_BOT_TOKEN is missing in .env")

        session_file = os.getenv("SESSION_FILE", "worker_video_1")
        logger.info(f"Connecting to Telegram with Worker Bot...")

        self.app = Client(
            name=session_file,
            api_id=int(os.getenv("TG_API_ID")),
            api_hash=os.getenv("TG_API_HASH"),
            bot_token=bot_token,
            workdir="/app/sessions" 
        )
        
        await self.app.start()
        me = await self.app.get_me()
        logger.info(f"SUCCESS: Worker @{me.username or me.id} connected on DC{me.dc_id}")

    async def main_loop(self):
        """Task Consumption Engine"""
        logger.info(f"Shadow Worker {self.worker_id} ready and idling.")
        while True:
            await asyncio.sleep(60)

async def main():
    worker = VideoWorker()
    try:
        await worker.init_services()
        await worker.main_loop()
    except Exception as e:
        logger.error(f"WORKER SHUTDOWN: {e}")
    finally:
        # Safe Stop logic
        if worker.app and worker.app.is_connected:
            await worker.app.stop()

if __name__ == "__main__":
    asyncio.run(main())
