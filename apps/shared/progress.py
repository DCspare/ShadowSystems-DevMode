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
        
    def update(self, current_size):
        now = time.time()
        interval = now - self.last_checkpoint_time
        
        # Only update speed every 1 second to keep it smooth
        if interval >= 1.0:
            # Current speed = (Size Diff) / (Time Diff)
            new_speed = (current_size - self.last_checkpoint_size) / interval
            # Moving average (80% old, 20% new) to prevent jitter
            self.current_speed = (self.current_speed * 0.8) + (new_speed * 0.2)
            
            self.last_checkpoint_size = current_size
            self.last_checkpoint_time = now
            
        return self.current_speed

    def get_eta(self, current_size):
        remaining = self.total_size - current_size
        if self.current_speed <= 0: return "∞"
        eta_seconds = remaining / self.current_speed
        return eta_seconds