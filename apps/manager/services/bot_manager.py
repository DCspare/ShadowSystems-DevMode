# apps/manager/services/bot_manager.py 
import os
import logging
from pyrogram import Client
from shared.settings import settings

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
        
        session_dir = "/app/sessions"
        if not os.path.exists(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        # Smart Plugin Loader
        # Tells Pyrogram to look in "handlers" folder for decorators
        plugins_config = dict(
            root="handlers" 
        )

        self.app = Client(
            name="manager_admin",
            api_id=settings.TG_API_ID,
            api_hash=settings.TG_API_HASH,
            bot_token=settings.TG_BOT_TOKEN,
            workdir=session_dir,
            plugins=plugins_config # <--- Auto-loads leech.py
        )
        
        await self.app.start()
        me = await self.app.get_me()
        logger.info(f"✅ Manager Brain Online: @{me.username}")

    async def stop(self):
        """Safe shutdown"""
        if self.app:
            try:
                await self.app.stop()
            except:
                pass
            logger.info("Manager Bot disconnected.")

# Critical instance name that main.py expects
bot_manager = ShadowBot()
