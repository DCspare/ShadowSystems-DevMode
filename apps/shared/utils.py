# apps/shared/utils.py 
import time
import string
import random
import psutil
import logging
from html import escape
from typing import List

logger = logging.getLogger("KernelUtils")

def generate_short_id(length: int = 7) -> str:
    """
    Shadow Logic: Generates a URL-friendly unique identifier (Base62).
    Used as 'short_id' in the library schema.
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

class ProgressManager:
    """Standardized UI math for the Shadow Systems V2 protocol."""
    
    @staticmethod
    def get_readable_file_size(size_in_bytes) -> str:
        if not size_in_bytes: return "0B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_in_bytes < 1024: return f"{size_in_bytes:.2f}{unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f}PB"

    @staticmethod
    def get_readable_time(seconds: int) -> str:
        periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
        result = ""
        for period_name, period_seconds in periods:
            if seconds >= period_seconds:
                period_value, seconds = divmod(seconds, period_seconds)
                result += f"{int(period_value)}{period_name}"
        return result or "0s"

    @staticmethod
    def get_bar(pct, length=12) -> str:
        pct = float(pct)
        p = min(max(pct, 0), 100)
        cFull = int(p // (100 / length))
        return f"[{'■' * cFull}{'□' * (length - cFull)}]"

class SystemMonitor:
    """Captures hardware stats matching MLTB standard."""
    
    @staticmethod
    def get_stats(download_dir: str = "/app/downloads"):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        try:
            free = psutil.disk_usage(download_dir).free
        except:
            free = 0
        return {
            "cpu": cpu,
            "mem": mem,
            "free": ProgressManager.get_readable_file_size(free)
        }

async def resolve_peers(client, chat_ids: List):
    """
    Shadow Deep-Probe Handshake:
    Forces Telegram to reveal the Access Hash by trying multiple MTProto paths.
    """
    logger.info("📡 Starting Deep-Probe Handshake...")
    resolved = 0
    
    for cid in chat_ids:
        if not cid or cid == 0: continue
        success = False
        
        # Method 1: Send a silent chat action (Fastest)
        try:
            from pyrogram.enums import ChatAction
            await client.send_chat_action(cid, ChatAction.TYPING)
            success = True
        except: pass

        # Method 2: Attempt to fetch the last message (Most effective for caching)
        if not success:
            try:
                async for _ in client.get_chat_history(cid, limit=1):
                    break
                success = True
            except: pass

        # Method 3: Last Ditch - Export Invite Link (Forces server lookup)
        if not success:
            try:
                # This often bypasses PeerIdInvalid if bot is admin
                await client.get_chat_member(cid, "me")
                success = True
            except: pass

        if success:
            try:
                chat = await client.get_chat(cid)
                logger.info(f"✅ Resolved: {chat.title} ({cid})")
                resolved += 1
            except: pass
        else:
            logger.error(f"❌ Deep-Probe Failed for {cid}. "
                         f"Bot needs a message update to learn this hash.")

    logger.info(f"🛰️ Handshake Phase Complete. Resolved {resolved} peers.")

def is_authorized(user_id: int) -> bool:
    """Checks if a user is the owner or a sudo user."""
    # We will expand this to check a 'sudo_users' list in settings later
    return user_id == settings.TG_OWNER_ID