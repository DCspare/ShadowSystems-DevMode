import os
import logging
from pyrogram import Client
from core.config import settings

logger = logging.getLogger("BotManager")

class ShadowBot:
    """
    Manager Bot Service (The Brain)
    Handles metadata ingestion and admin commands.
    """
    def __init__(self):
        self.app = None

    async def start(self):
        """Initializes and starts the Pyrogram Client"""
        logger.info("Starting Manager Bot...")
        
        # Absolute path within the container mount
        session_dir = "/app/sessions"
        
        # Ensure directory exists and is writable
        if not os.path.exists(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        # Initialize Client
        # Identity Logic: Always use Bot Token for the Manager Brain
        self.app = Client(
            name="manager_admin",
            api_id=settings.TG_API_ID,
            api_hash=settings.TG_API_HASH,
            bot_token=settings.TG_BOT_TOKEN,
            workdir=session_dir
        )
        
        await self.app.start()
        me = await self.app.get_me()
        logger.info(f"Manager Bot active as @{me.username}")

    async def stop(self):
        """Safe shutdown of the client"""
        if self.app:
            try:
                await self.app.stop()
                logger.info("Manager Bot disconnected.")
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")

# Critical instance name that main.py expects
bot_manager = ShadowBot()
