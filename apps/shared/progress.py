# apps/shared/progress.py
import time


class TaskProgress:
    """
    MLTB-Inspired Progress Tracker.
    Calculates moving average speed and stable ETA.
    """
    def __init__(self, total_size):
        self.total_size = total_size
        self.start_time = time.time()
        self.last_checkpoint_size = 0
        self.last_checkpoint_time = self.start_time
        self.current_speed = 0

    @staticmethod
    def human_size(num):
        """Converts bytes to MB/GB."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if num < 1024.0: return f"{num:.2f}{unit}"
            num /= 1024.0
        return f"{num:.2f}PB"

    def update(self, current_size) -> float:
        """
        Calculates and returns the current speed in bytes/second.
        Returns a raw float, not a formatted string.
        """
        now = time.time()
        interval = now - self.last_checkpoint_time

        # Only update speed every 1 second to keep it smooth
        if interval >= 1.0:
            # Current speed = (Size Diff) / (Time Diff)
            new_speed = (current_size - self.last_checkpoint_size) / interval
            # Exponential Moving Average (80% old, 20% new) to prevent jitter
            self.current_speed = (self.current_speed * 0.8) + (new_speed * 0.2)

            self.last_checkpoint_size = current_size
            self.last_checkpoint_time = now

        return self.current_speed

    def get_formatted_speed(self) -> str:
        """
        Returns the current speed as a human-readable string (e.g., "12.5 MB/s").
        """
        return self.human_size(self.current_speed) + "/s"

    def get_eta(self, current_size):
        remaining = self.total_size - current_size
        if self.current_speed <= 0: return "∞"
        eta_seconds = remaining / self.current_speed

        # Format ETA to MM:SS or HH:MM:SS
        m, s = divmod(int(eta_seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
