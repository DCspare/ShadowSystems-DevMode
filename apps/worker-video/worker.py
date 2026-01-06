import asyncio
import logging
import os
from pyrogram import Client, filters
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from handlers.leech import MediaLeecher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VideoWorker")

class VideoWorker:
    def __init__(self):
        self.app = None
        self.db = None
        self.redis = None
        self.leecher = None
        self.worker_id = os.getenv("WORKER_ID", "video_worker_1")

    async def init_services(self):
        mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
        self.db = mongo_client["shadow_systems"]
        self.redis = Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        
        self.app = Client(
            name=os.getenv("SESSION_FILE", "worker_v1"),
            api_id=int(os.getenv("TG_API_ID")),
            api_hash=os.getenv("TG_API_HASH"),
            bot_token=os.getenv("TG_WORKER_BOT_TOKEN"),
            workdir="/app/sessions" 
        )

        @self.app.on_message(filters.command("register") & filters.group)
        async def register_handler(c, m):
            logger.info(f"Registered with Chat {m.chat.id}")
            await m.reply_text("✅ Chat Registered in Session Cache.")

        await self.app.start()
        self.leecher = MediaLeecher(self.app, self.db)
        logger.info(f"Worker online as @{(await self.app.get_me()).username}")

    async def task_watcher(self):
        """Shadow Bridge: Watch Redis for manual attachment tasks"""
        logger.info("Task Watcher started. Listening to 'queue:leech'...")
        while True:
            try:
                task = await self.redis.brpop("queue:leech", timeout=10)
                if task:
                    # task = ['queue:leech', '27205|/app/test_video.mp4']
                    tmdb_id, file_path = task[1].split("|")
                    logger.info(f"Consumed task: tmdb_{tmdb_id} with file {file_path}")
                    
                    # Process via the Handlers
                    await self.leecher.upload_and_sync(file_path, int(tmdb_id))
            except Exception as e:
                logger.error(f"Task Processor Error: {e}")
            await asyncio.sleep(1)

async def main():
    worker = VideoWorker()
    await worker.init_services()
    await worker.task_watcher()

if __name__ == "__main__":
    asyncio.run(main())
