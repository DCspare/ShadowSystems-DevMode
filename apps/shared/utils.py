# apps/shared/utils.py 
import time
import string
import random
import psutil

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
    def get_bar(pct, length=10):
        filled = min(max(int(pct) // (100 // length), 0), length)
        return f"[{'■' * filled}{'□' * (length - filled)}]"

    @staticmethod
    def get_system_stats():
        """Captures stats like the big bots in your screenshots."""
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        # Simple uptime (System, not bot)
        uptime_seconds = time.time() - psutil.boot_time()
        hours, remainder = divmod(int(uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"CPU: {cpu}% | RAM: {ram}% | UPTIME: {hours}h{minutes}m"