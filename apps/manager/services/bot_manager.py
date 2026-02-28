# apps/manager/services/bot_manager.py
import logging

from shared.tg_client import TgClient

TgClient.setup_logging()
logger = logging.getLogger("BotManager")

class ShadowManager:
    """
    Manager Bot Service (The Brain)
    Handles metadata ingestion and admin commands.
    """
    async def start(self):
        """Initializes and starts the Pyrogram Client"""
        logger.info("Starting Manager Bot...")

        # Smart Plugin Loader
        # Tells Pyrogram to look in "handlers" folder for decorators
        plugins_config = dict(
            root="handlers"
        )

         # 1. Initialize Identities (Bot vs User)
        await TgClient.start_bot(name="manager_bot", plugins=plugins_config)
        await TgClient.start_user()

        # Determine the primary handler (Usually Bot for Admin Commands)
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
