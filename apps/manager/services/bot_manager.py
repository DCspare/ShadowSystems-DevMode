# apps/manager/services/bot_manager.py 
import os 
import logging
from shared.tg_client import TgClient

logger = logging.getLogger("BotManager")

class ShadowManager:
    """
    Manager Bot Service (The Brain)
    Handles metadata ingestion and admin commands.
    """  
    async def start(self):
        """Initializes and starts the Pyrogram Client"""
        logger.info("Starting Manager Bot...")
        
        # We start Bot vs User 
        await TgClient.start_bot(name="manager_bot")
        await TgClient.start_user()

        self.app = TgClient.bot or TgClient.user # Link for handler compatibility

        # 🛰️ Enable Verification Pulse for Manager
        await TgClient.send_startup_pulse("MANAGER-BRAIN")
        logger.info(f"✅ Manager Brain Online: @{self.app.me.username}")

    @property
    def client(self):
        return TgClient.bot

    async def stop(self):
        """Safe shutdown"""
        await TgClient.stop()
        logger.info("Manager Bot disconnected.")

# Alias for main.py compatibility
bot_manager = ShadowManager()
