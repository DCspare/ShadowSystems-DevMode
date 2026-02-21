# apps/shared/tg_client.py
import os
import asyncio
import logging
from pyrogram import raw # Need raw MTProto functions
from inspect import signature
from typing import Dict, Optional
from shared.settings import settings
from shared.database import db_service 
from pyrogram import Client, enums, handlers

logger = logging.getLogger("ShadowTG")

class TgClient:
    _lock = asyncio.Lock()
    _hlock = asyncio.Lock()
    _synced_peers = set() # 🔒 Tracked memory for handshakes

    bot: Client = None
    user: Client = None
    helper_bots: Dict[int, Client] = {}
    helper_loads: Dict[int, int] = {}

    IS_PREMIUM_USER = False
    MAX_SPLIT_SIZE = 2097152000

    @classmethod
    def setup_logging(cls):
        """Forces unified logging format across all nodes (Manager/Worker)"""
        handler = logging.StreamHandler()
        # Clean consistent format: 2026-02-11 12:00:00 - NodeName - LEVEL - Message
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        
        # Reset and apply to root to stop Uvicorn/Pyrogram from making a mess
        root = logging.getLogger()
        for h in root.handlers[:]: root.removeHandler(h)
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    @classmethod
    def create_pyro_client(cls, name: str, bot_token: str = None, session_string: str = None, no_updates: bool = False, plugins: dict = None):
        """Unified Client Builder"""
        kwargs = {
            "api_id": settings.TG_API_ID,
            "api_hash": settings.TG_API_HASH,
            "parse_mode": enums.ParseMode.HTML,
            "in_memory": settings.USE_IN_MEMORY_SESSION, # 🔑 Toggle via settings
            "workdir": "/app/sessions",
            "plugins": plugins # 🔑 Optional Plugins
        }

        # 🔑 PRIORITY: Bot Token > Session String
        if bot_token and len(bot_token) > 10:
            kwargs["bot_token"] = bot_token
        elif session_string and len(session_string) > 20:
            kwargs["session_string"] = session_string

        # Max Performance Tuning from WZML-X
        # In apps/shared/tg_client.py

    @classmethod
    def create_pyro_client(cls, name: str, bot_token: str = None, session_string: str = None, no_updates: bool = False, plugins: dict = None):
        """Unified Client Builder with enhanced network stability."""
        kwargs = {
            "api_id": settings.TG_API_ID,
            "api_hash": settings.TG_API_HASH,
            "parse_mode": enums.ParseMode.HTML,
            "in_memory": settings.USE_IN_MEMORY_SESSION,
            "workdir": "/app/sessions",
            "plugins": plugins
        }

        if bot_token and len(bot_token) > 10:
            kwargs["bot_token"] = bot_token
        elif session_string and len(session_string) > 20:
            kwargs["session_string"] = session_string

        # ✅ FIX: Add robust connection and timeout settings
        # Increase retries for network flaps and set a longer timeout for operations.
        for param, value in {
            "max_concurrent_transmissions": 100,
            "sleep_threshold": 120, # Increase flood wait tolerance
            "connection_retries": 5, # Retry up to 5 times on connection errors
            "timeout": 30 # Set a 30-second timeout for API calls
        }.items():
            if param in signature(Client.__init__).parameters:
                kwargs[param] = value

        return Client(name, no_updates=no_updates, **kwargs)

        return Client(name, no_updates=no_updates, **kwargs)

    @classmethod
    async def start_bot(cls, name: str = "ShadowBot", token_override: str = None, plugins: dict = None):
        """Starts the Primary Bot identity for the specific node (Manager or Worker)"""
        target_token = token_override or settings.TG_BOT_TOKEN
        if not target_token or len(target_token) < 10:
            logger.warning(f"⚠️ No Bot Token for {name}. Checking for User fallback...")
            return False
        
        async with cls._lock:
            if cls.bot: return True
            cls.bot = cls.create_pyro_client(name, bot_token=target_token, plugins=plugins)
            await cls.bot.start()
            cls.register_refresh_handler(cls.bot)
            logger.info(f"✅ Bot Identity [@{cls.bot.me.username}] is ONLINE.")
            return True

    @classmethod
    async def start_user(cls):
        """Muscle identity (Only starts if WORKER_MODE is USER or not set)"""
        mode = os.getenv("WORKER_MODE", "BOT").upper()
        
        # 🛡️ PROTECT ACCOUNT: Workers in BOT mode don't need User identities.
        if mode == "BOT":
            logger.info("ℹ️ WORKER_MODE=BOT. Skipping User Session connection for safety.")
            return

        if settings.TG_SESSION_STRING and len(settings.TG_SESSION_STRING) > 20:
            logger.info("📡 WORKER_MODE=USER. Initializing Muscle...")
            try:
                cls.user = cls.create_pyro_client(
                    "ShadowUser", 
                    session_string=settings.TG_SESSION_STRING,
                    no_updates=True
                )
                await cls.user.start()
                cls.IS_PREMIUM_USER = cls.user.me.is_premium
                cls.MAX_SPLIT_SIZE = 4194304000 if cls.IS_PREMIUM_USER else 2097152000
                
                uname = cls.user.me.username or cls.user.me.first_name
                logger.info(f"⚡ User: [{uname}] Premium: {cls.IS_PREMIUM_USER} Connected.")
            except Exception as e:
                logger.error(f"❌ User Session Fail: {e}")
                cls.user = None
        else:
            logger.info("ℹ️ User Session (MTProto) is disabled. Using Bot Mode.")
            cls.user = None

    @classmethod
    async def start_helpers(cls):
        """Initializes the Swarm (Helper Bots) if HELPER_TOKENS exist"""
        if not settings.HELPER_TOKENS or len(settings.HELPER_TOKENS) < 5:
            logger.info("ℹ️ Helper Bots Swarm is disabled.")
            return
        
        tokens = settings.HELPER_TOKENS.split()
        # Filter out invalid entries like '0'
        tokens = [t for t in tokens if len(t) > 10]
        
        if not tokens:
            return

        logger.info(f"🐝 Spinning up {len(tokens)} Helper Bots...")

        async def start_h(idx, token):
            try:
                h_bot = await cls.create_pyro_client(f"Helper-{idx}", bot_token=token, no_updates=True).start()
                cls.helper_bots[idx] = h_bot
                cls.helper_loads[idx] = 0
            except Exception as e:
                logger.error(f"❌ Helper {idx} Fail: {e}")

        async with cls._hlock:
            await asyncio.gather(*(start_h(i, t) for i, t in enumerate(tokens, 1)))

    @classmethod
    def register_refresh_handler(cls, client: Client):
        """Shared Peer Seeder: Syncs AccessHash only when needed"""
        async def refresh_peer_logic(client, message):
            targets = [settings.TG_LOG_CHANNEL_ID, settings.TG_BACKUP_CHANNEL_ID]
            # 🛡️ FIX 1: Only log and sync if we haven't already this session
            if message.chat.id in targets and message.chat.id not in cls._synced_peers:
                # Triggers Peer Update
                await client.resolve_peer(message.chat.id)
                cls._synced_peers.add(message.chat.id)
                logger.info(f"⚡ Peer Handshake Refreshed: {message.chat.title or message.chat.id}")

        client.add_handler(handlers.MessageHandler(refresh_peer_logic))

    @classmethod
    async def resolve_peers(cls):
        """Standard Peer Discovery + Redis Brain Sync"""
        target_ids = [settings.TG_LOG_CHANNEL_ID, settings.TG_BACKUP_CHANNEL_ID]
        valid_ids = [i for i in target_ids if i and i != 0]
        
        for cid in valid_ids:
            try:
                # 🛠️ STRATEGY: Directly resolve the peer. 
                # If the bot has ever seen the group, this succeeds.
                await cls.bot.resolve_peer(cid)

                # Check get_chat to ensure it's in the SQLite local DB
                await cls.bot.get_chat(cid)

                if cid not in cls._synced_peers:
                    cls._synced_peers.add(cid)
                    logger.info(f"🛰️ Peer Seeded: {cid}")
            except Exception as e:
                # Log only once on failure
                if cid not in cls._synced_peers:
                    logger.warning(f"⚠️ Handshake missing for {cid}: {e}. Waiting for 1 message...")

    @classmethod
    async def send_startup_pulse(cls, node_name: str):
        """Broadcasts pulse to all critical channels to trigger auto-discovery for peers"""
        # 🔑 Step A: First Hydrate memory
        await cls.resolve_peers()
        
        target_ids = [settings.TG_LOG_CHANNEL_ID, settings.TG_BACKUP_CHANNEL_ID]
        valid_ids = [i for i in target_ids if i and i != 0]

        # Fetch current mode for the message
        mode = os.getenv("WORKER_MODE", "BOT").upper()
        
        for cid in valid_ids:
            try:
                text=(
                    f"<pre>Shadow Handshake: <b>ONLINE</b></pre>\n"
                    f"┌ {'—' * 12}\n"
                    f"├ <b>Name</b>: @{cls.bot.me.username}\n"
                    f"├ <b>Node</b>: <code>{node_name}</code>\n"
                    f"├ <b>Mode</b>: <code>{mode}</code>\n"  
                    f"└ <b>Storage</b>: {'RAM' if settings.USE_IN_MEMORY_SESSION else 'DISK'}"
                    f"{' (Premium)' if cls.IS_PREMIUM_USER else ''}"
                )
                # me = await cls.bot.get_me()
                msg = await cls.bot.send_message(
                    chat_id=cid,
                    text=text
                )
                await asyncio.sleep(10)
                await msg.delete()
                logger.info(f"✅ Peer Probe successful for {cid} from {node_name}")
            except Exception as e:
                # We catch it so the container doesn't restart, allowing for manual debugging
                logger.error(f"❌ Failed to seed Peer {cid} from {node_name}: {e}") 

    @classmethod
    async def get_client(cls, user_required=False):
        """Priority Router: Returns Identity based on WORKER_MODE"""
        mode = os.getenv("WORKER_MODE", "BOT").upper()
        
        # 🤖 BOT PRIORITY
        if mode == "BOT":
            return cls.bot
        
        # 👤 USER PRIORITY
        if cls.user:
            return cls.user
        return cls.bot

    @classmethod
    async def stop(cls):
        async with cls._lock:
            tasks = []
            if cls.bot: 
                tasks.append(cls.bot.stop())
            if cls.user: 
                tasks.append(cls.user.stop())
            if cls.helper_bots:
                tasks.extend([h.stop() for h in cls.helper_bots.values()])

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("📴 All Clients Shutdown.")