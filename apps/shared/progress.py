# apps/shared/progress.py
import time
import math
import logging

class ShadowProgress:
    """
    Unified Terminal Progress Bar (TUI).
    Renders: ⬇️ [██████----] 60% | ⚡ 4.2 MB/s | ⏱️ 10s
    throttles logs to prevent Docker flooding.
    """
    def __init__(self):
        self.logger = logging.getLogger("Progress")
        self._last_log_time = 0
        self._log_interval = 5.0 # Max 1 update per 5 seconds

    def human_size(self, size_bytes):
        if not size_bytes: return ""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} PB"

    def human_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))

    def progress_bar_str(self, percentage):
        bar_len = 20
        filled = int(bar_len * percentage // 100)
        return "█" * filled + "-" * (bar_len - filled)

    def log(self, current, total, desc="Task", start_time=None):
        now = time.time()
        
        # Always log 100%, otherwise throttle
        if current != total and (now - self._last_log_time) < self._log_interval:
            return

        self._last_log_time = now
        
        percentage = 0
        if total > 0:
            percentage = min(int((current / total) * 100), 100)

        # Speed / ETA logic
        speed_str = ""
        eta_str = ""
        if start_time and current > 0:
            elapsed = now - start_time
            speed = current / elapsed if elapsed > 0 else 0
            speed_str = f"⚡ {self.human_size(speed)}/s"
            
            if speed > 0 and total > 0:
                remaining_bytes = total - current
                eta = remaining_bytes / speed
                eta_str = f"⏱️ {int(eta)}s"

        icon = "🔄" if percentage < 100 else "✅"
        bar = self.progress_bar_str(percentage)
        
        # using print(..., flush=True) directly to bypass python logging buffers
        # using \r to overwrite line is tricky in docker logs, straightforward print is safer for scrolling logs
        print(f"{icon} [{bar}] {percentage}% | {desc} | {self.human_size(current)}/{self.human_size(total)} | {speed_str} {eta_str}", flush=True)

# Global Instance
progress_bar = ShadowProgress()