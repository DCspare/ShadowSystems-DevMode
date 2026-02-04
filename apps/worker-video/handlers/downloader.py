# apps/worker-video.handlers/downloader.py  
import os
import sys
import time
import aria2p
import yt_dlp
import asyncio
import logging
from shared.utils import ProgressManager
from shared.progress import TaskProgress
from shared.registry import task_dict, task_dict_lock, MirrorStatus 

logger = logging.getLogger("Downloader")

class Downloader:
    def __init__(self, download_path="/app/downloads"):
        self.download_path = download_path
        self.aria2 = None
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)

    async def initialize(self, redis=None, ui_callback=None):
        self.redis = redis
        self.ui_callback = ui_callback # THE BRIDGE

        try:
            self.aria2 = aria2p.API(
                aria2p.Client(host="http://localhost", port=6800, secret="")
            )
            logger.info("✅ Connected to Aria2 Daemon")
        except Exception:
            self.aria2 = None

    async def _update_status(self, pct, downloaded, total, speed, eta):
        """Helper to safely write to the global task dictionary."""
        async with task_dict_lock:
            if self.current_task_id in task_dict:
                task_dict[self.current_task_id].update({
                    "progress": pct,
                    "processed": ProgressManager.get_readable_file_size(downloaded),
                    "size": ProgressManager.get_readable_file_size(total),
                    "speed": speed,
                    "eta": eta,
                    "status": MirrorStatus.STATUS_DOWNLOAD
                })

    def _native_logger_progress(self, d):
        """Reports data to the Shared Registry for StatusManager to display."""
        if d['status'] == 'downloading':
            try:
                # Capture current state into class attributes
                # This allows worker.py to read progress without freezing yt-dlp
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total <= 0: return
                
                if not self.tracker:
                    from shared.progress import TaskProgress
                    self.tracker = TaskProgress(total)

                    # ✅ SYNC-SAFE REGISTRY UPDATE
                    # We update the dictionary so the StatusManager Heartbeat can see it
                    task_id = self.current_task_id
                    
                speed_raw = self.tracker.update(downloaded)
                eta_raw = self.tracker.get_eta(downloaded)
                pct = int(downloaded * 100 / total)
                    
                speed_fmt = ProgressManager.get_readable_file_size(speed_raw) + "/s"
                eta_fmt = ProgressManager.get_readable_time(int(eta_raw)) if isinstance(eta_raw, (int, float)) else "..."
                        
                # ✅ USE THREAD-SAFE DICTIONARY UPDATE
                # Instead of run_coroutine_threadsafe, we update the dict directly
                # Python dict updates are thread-safe in CPython for this use case
                if self.current_task_id in task_dict:
                    task_dict[self.current_task_id].update({
                        "progress": pct,
                        "processed": ProgressManager.get_readable_file_size(downloaded),
                        "size": ProgressManager.get_readable_file_size(total),
                        "speed": speed_fmt,
                        "eta": eta_fmt,
                        "status": MirrorStatus.STATUS_DOWNLOAD
                    })

                # Terminal (Every 10%)
                if pct % 10 == 0 and pct != getattr(self, '_last_print_pct', -1):
                    self._last_print_pct = pct
                    sys.stdout.write(f"⬇️ [DL] {pct}% | {speed_fmt} | ETA: {eta_fmt}\n")
                    sys.stdout.flush()
                        
                # Check Kill Signal
                if self.redis:
                    # Sync check in thread
                    pass 
            except Exception: pass
        elif d['status'] == 'finished':
            sys.stdout.write(f"✅ [DL] Download Phase Complete. Finalizing...\n") 
            sys.stdout.flush()

    def _get_safe_filename(self, candidate, default="video"):
        """Prevents Errno 36 (Filename too long)"""
        if not candidate: 
            return f"{default}_{int(time.time())}.mp4"
            
        # Clean URL query params if they leaked in
        clean = candidate.split("?")[0]
        
        # Truncate if insanely long (Linux limit is 255, we target 200)
        if len(clean) > 200:
            ext = os.path.splitext(clean)[1]
            if not ext or len(ext) > 5: ext = ".mp4"
            return f"truncated_name_{int(time.time())}{ext}"
            
        return clean

    def get_direct_url(self, url: str) -> dict:
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'nocheckcertificate': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Analyzing: {url}")
                info = ydl.extract_info(url, download=False)

                # Check direct
                if info.get('direct'):
                     # Sanitization
                    safe_name = self._get_safe_filename(os.path.basename(url), "direct_video")
                    return {"url": url, "filename": safe_name, "type": "direct"}
                
                # Extract meta
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                safe_name = self._get_safe_filename(f"{title}.{ext}", "stream")

                return {
                    "url": info.get('url'), 
                    "filename": safe_name,
                    "type": "video_site"
                }
        except:
            # Fallback for raw URLs failing inspection
            raw_name = url.split("/")[-1]
            safe_name = self._get_safe_filename(raw_name, "raw_download")
            return {"url": url, "filename": safe_name, "type": "raw"}

    async def start_download(self, target: dict, task_id: str = None) -> str:
        self.current_task_id = task_id
        self.current_pct = 0 # Initialize for worker to read
        self._last_pct = -1 # Reset for new file
        self.tracker = None # We assume size is 0 and update it once yt-dlp starts
        raw_link = target['url']
        fname = self._get_safe_filename(target.get('filename'), "video.mp4")
        final_path = os.path.join(self.download_path, fname)

        async with task_dict_lock:
            if task_id in task_dict:
                task_dict[task_id].update({
                    "status": MirrorStatus.STATUS_DOWNLOAD,
                    "eta": "Probing..."
                })

        # 1. Kill Switch Check (Initial)
        if task_id and self.redis:
            if await self.redis.get(f"kill_signal:{task_id}"):
                raise Exception("TASK_CANCELLED_BEFORE_START")
            await self.redis.hset(f"task_status:{task_id}", "status", "downloading")

        # Route to Engine (Magnet -> Aria2)
        if raw_link.startswith("magnet:") or ".torrent" in raw_link:
            return await self.download_with_aria2(raw_link, task_id)

        # HTTP/Native Mode
        logger.info(f"🌐 Downloader: YT-DLP Native Mode for {task_id}")
        try:
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best', # Allow merging
                'outtmpl': f"{self.download_path}/%(title)s.%(ext)s",
                'nocheckcertificate': True,
                'progress_hooks': [self._native_logger_progress],
                'quiet': True, 
                'no_warnings': True,
                # Ensure it sees the cookie file mapped in Docker
                'cookiefile': os.getenv("COOKIES_FILE_PATH", "/app/cookies.txt"),
                'trim_file_name': 200,
                # Fixes permission errors by restricting weird characters
                'restrictfilenames': True 
            }
            # Custom overwrite for raw to enforce our safe name
            if target.get('type') == 'raw' or target.get('type') == 'direct':
                ydl_opts['outtmpl'] = final_path

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._native_run(raw_link, ydl_opts))
            
            # Locate file (handle edge cases where yt-dlp changes extension)
            if os.path.exists(final_path): return final_path
            
            # Fuzzy match finder if name changed
            for f in os.listdir(self.download_path):
                # Check if file part name matches or if it matches the safe target we requested
                if fname in f or (task_id and task_id in f): 
                    return os.path.join(self.download_path, f)
                    
            return final_path # Hope

        except Exception as e:
            logger.error(f"DL Failed: {e}")
            raise e

    def _native_run(self, url, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def download_with_aria2(self, raw_link, task_id):
        if not self.aria2: await self.initialize()
        logger.info("🧲 Sending Magnet to Aria2 Daemon...")

        try:
            # Added aria2 options to disable seeding and force save
            options = {
                'dir': self.download_path,
                'seed-time': '0' # Stops seeding immediately after download finishes
            }
             # 1. Add Magnet
            gid = self.aria2.add_uris([raw_link], options={'dir': self.download_path}).gid
            logger.info(f"🧲 Aria2: Started {task_id} (GID: {gid})")

            # Use raw GID to fetch fresh objects each time
            download = self.aria2.get_download(gid)

            # Initial placeholder
            print("⏳ Initializing Aria2 stream...", flush=True)
            
            # 2. Tracking Loop
            while True:
                try:
                    download = self.aria2.get_download(gid)
                except aria2p.client.ClientException:
                    # Handle race condition where file finishes and is removed quickly
                    break 
                
                # Check for Metadata Handoff 
                if download.followed_by:
                    # behavior: aria2p returns ID strings or objects depending on version
                    # We treat it defensively
                    next_dl = download.followed_by[0]
                    new_gid = next_dl.gid if hasattr(next_dl, 'gid') else next_dl 
                    print(f"\n🧲 Metadata Retrieved Handover: {gid} -> {new_gid}", flush=True)
                    # logger.info(f"🧲 Metadata Retrieved Handover: {gid} -> {new_gid}")
                    gid = new_gid # Switch our tracking target ID
                    continue # Restart loop with new GID

                # ERROR Handling
                if download.status == 'error':
                    print("") # Clear line
                    raise Exception(f"Aria2 Error {download.error_code}: {download.error_message}")
                
                # Enhanced completion check (Check Length OR Status)
                if download.is_complete or \
                   download.status == 'complete' or \
                   (download.total_length > 0 and download.completed_length >= download.total_length):
                    print("\n✅ Download Complete.") # Newline to finalize the bar
                    # logger.info("✅ 🧲 Download Complete. Processing...")
                    break
                    
                 # LIVE PROGRESS BAR
                if download.total_length > 0:
                    pct = int(download.completed_length * 100 / download.total_length)
                    
                    # Create a visual bar [█████------]
                    bar_len = 25 
                    filled_len = int(bar_len * pct // 100)
                    bar = '█' * filled_len + '-' * (bar_len - filled_len)
                    
                    # \r = return to start of line, end='' = don't add new line
                    msg = f"\r🧲 [{bar}] {pct}% | ⚡ {download.download_speed_string()} | 📦 {download.total_length_string()}"
                    print(msg, end='', flush=True)

                # --- KILL SWITCH (MID-MAGNET) ---
                if task_id and self.redis:
                    if await self.redis.get(f"kill_signal:{task_id}"):
                        self.aria2.remove([gid], force=True, clean=True)
                        raise Exception("ABORTED_BY_SIGNAL")
                
                # Faster refresh rate for smooth UI
                await asyncio.sleep(2)

            # 3. Resolve File Path
            # Refetch one last time to get the final list on disk
            try:
                download = self.aria2.get_download(gid)
            except:
                pass # Proceed, assuming files are on disk if loop broke
            
            # Torrents often contain multiple files. We pick the largest video.
            largest_file = None
            max_size = 0

            if not download.files:
                 # Backup scan of folder if Aria2 info is gone
                 logger.warning("Aria2 API lost file list, scanning folder...")
                 files = os.listdir(self.download_path)
                 if not files: raise Exception("No files found after download")
                 return os.path.join(self.download_path, files[0])
            
            for f in download.files:
                # f.path matches disk
                if f.length > max_size and str(f.path).lower().endswith(('.mp4', '.mkv', '.avi', '.ts')):
                    max_size = f.length
                    largest_file = f.path
            
            if not largest_file and len(download.files) > 0:
                 # Fallback: Just take the first file if no video found
                 largest_file = download.files[0].path

            # Cleanup Aria2 list (Optional but good practice)
            try:
                self.aria2.remove([gid])
            except: 
                pass
                 
            return str(largest_file)

        except Exception as e:
            logger.error(f"Aria2 Fatal Logic: {e}")
            raise e

downloader = Downloader()