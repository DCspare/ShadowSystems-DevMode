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

    async def _update_status(self, pct, downloaded, total, speed, eta, task_id):
        """Helper to safely write to the global task dictionary."""
        async with task_dict_lock:
            if task_id in task_dict:
                task_dict[task_id].update({
                    "progress": pct,
                    "processed": ProgressManager.get_readable_file_size(downloaded),
                    "size": ProgressManager.get_readable_file_size(total),
                    "speed": speed,
                    "eta": eta,
                    "status": MirrorStatus.STATUS_DOWNLOADING 
                })

    def _get_native_progress_hook(self, task_id):
        """Reports data to the Shared Registry for StatusManager to display."""
        # Stores state locally for this specific download instead of globally on `self`
        state = {"tracker": None, "last_pct": -1} 

        def _hook(d):
            if d.get('status') == 'downloading':
                try:
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if total <= 0: return
                    
                    if state["tracker"] is None:
                        from shared.progress import TaskProgress
                        state["tracker"] = TaskProgress(total)
                        
                    tracker = state["tracker"]
                    speed_raw = tracker.update(downloaded)
                    # Ensure progress.py has get_formatted_speed() or use human_size
                    speed_fmt = tracker.get_formatted_speed() 
                    eta_raw = tracker.get_eta(downloaded)
                    eta_fmt = ProgressManager.get_readable_time(int(eta_raw)) if isinstance(eta_raw, (int, float)) else "..."
                    pct = int(downloaded * 100 / total)
                            
                    # ✅ Thread-safe dict update using the isolated task_id
                    if task_id in task_dict:
                        task_dict[task_id].update({
                            "progress": pct,
                            "processed": ProgressManager.get_readable_file_size(downloaded),
                            "size": ProgressManager.get_readable_file_size(total),
                            "speed": speed_fmt,
                            "eta": eta_fmt,
                            "status": MirrorStatus.STATUS_DOWNLOADING 
                        })

                    # Terminal Output formatting fixed to prevent console spam
                    if pct % 5 == 0 and pct != state["last_pct"]:
                        state["last_pct"] = pct
                        print(f"\r⬇️ [DL] {pct}% | {speed_fmt} | ETA: {eta_fmt}", end="", flush=True)
                except Exception as e:
                    logger.error(f"Hook Error: {e}")
            elif d == 'finished':
                print(f"\n✅ Download Phase Complete.\n", flush=True)
                
        return _hook

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
        # ✅ FIX: Removed unsafe self.current_task_id and self.tracker assignments here
        raw_link = target.get('url') 
        if not raw_link:
            raise ValueError("Target dictionary is missing the 'url' key.")

        fname = self._get_safe_filename(target.get('filename'), "video.mp4")
        final_path = os.path.join(self.download_path, fname)

        async with task_dict_lock:
            if task_id in task_dict:
                task_dict[task_id].update({
                    "status": MirrorStatus.STATUS_DOWNLOADING, # ✅ FIX: Typo Corrected
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
                'progress_hooks': [self._get_native_progress_hook(task_id)],
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
            await loop.run_in_executor(None, self._native_run, raw_link, ydl_opts)
            
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
        logger.info(f"🧲 Handshaking with Aria2 for task {task_id}...")

        try:
            # Added aria2 options to disable seeding and force save
            options = {
                'dir': self.download_path,
                'seed-time': '0' # Stops seeding immediately after download finishes
            }
            # 1. Add Magnet
            try:
                download = self.aria2.add_uris([raw_link], options=options)
                gid = download.gid
            except Exception as e:
                if "already registered" in str(e).lower():
                    # Self-Healing: If already exists, find it and track it instead of failing
                    logger.warning("🧲 InfoHash exists. Attaching to existing stream...")
                    # Extract info-hash from magnet if possible or just check active downloads
                    for dl in self.aria2.get_downloads():
                        # We try to match by URI or InfoHash logic
                        # Simplified: find the first one with the same status
                        if dl.status in ['active', 'waiting', 'paused']:
                             gid = dl.gid
                             break
                    else: raise e # Re-raise if we can't find it
                else: raise e

            logger.info(f"🧲 Aria2: Tracking GID {gid}")

            # Initial placeholder
            print("⏳ Initializing Aria2 stream...", flush=True)
            
            # 2. Tracking Loop
            while True:
                try:
                # RE-FETCH every time to ensure we have an OBJECT, not a string
                    download = self.aria2.get_download(gid)
                except Exception:
                    break # Usually means it finished and was removed 
                
                # A. Handle Metadata -> Torrent Handover
                if download.followed_by:
                    # In metadata mode, 'followed_by' is a list of NEW GID strings
                    new_item = download.followed_by[0]
                    gid = new_item.gid if not isinstance(new_item, str) else new_item
                    logger.info(f"🧲 Metadata phase complete. Switching to File GID: {gid}")
                    # Force update dictionary status
                    async with task_dict_lock:
                        if task_id in task_dict:
                            task_dict[task_id].update({"eta": "Starting file..."})
                    continue 

                # B. Handle Completion or Errors (Check Length OR Status)
                if download.is_complete or \
                   download.status == 'complete' or \
                   (download.total_length > 0 and download.completed_length >= download.total_length):
                    print("\n✅ Download Complete.") # Newline to finalize the bar
                    logger.info(f"✅ Aria2 Download Finished: {gid}")
                    break

                # ERROR Handling
                if download.status == 'error':
                    err_msg = download.error_message or "Unknown Aria2 Error"
                    raise Exception(f"Aria2 Error: {err_msg}")
                                    
                # C. LIVE PROGRESS & PEER DISCOVERY LOGGING
                downloaded = download.completed_length
                total = download.total_length
                peers = getattr(download, 'connections', 0)
                speed = download.download_speed_string()

                if total > 0:
                    # --- ACTUAL FILE DOWNLOAD PHASE ---
                    pct = int(downloaded * 100 / total)
                    speed_fmt = download.download_speed_string()
                    eta_fmt = download.eta_string()

                    # Update Registry for /status UI
                    async with task_dict_lock:
                        if task_id in task_dict:
                            task_dict[task_id].update({
                                "progress": pct,
                                "processed": download.completed_length_string(),
                                "size": download.total_length_string(),
                                "speed": f"{speed_fmt}/s",
                                "eta": eta_fmt,
                                "status": MirrorStatus.STATUS_DOWNLOADING
                            })

                    # Terminal Output
                    if pct % 10 == 0:
                        print(f"\r🧲 [ARIA2] {pct}% | Speed: {speed_fmt} | ETA: {eta_fmt} | Peers: {peers}", end="", flush=True)
                
                else:
                    # --- METADATA / PEER DISCOVERY PHASE ---
                    # Update status message so UI/Logs don't look frozen
                    async with task_dict_lock:
                        if task_id in task_dict:
                            task_dict[task_id].update({
                                "status": MirrorStatus.STATUS_DOWNLOADING,
                                "speed": f"0B/s",
                                "eta": f"Conns: {peers} (Waiting for Metadata...)"
                            })
                    print(f"\r📡 [SEEDERS] Found: {peers} | Looking for metadata...", end="", flush=True)

                # D. KILL SWITCH Check (MID-MAGNET)
                if task_id and self.redis:
                    kill = await self.redis.get(f"kill_signal:{task_id}")
                    if kill:
                        logger.warning(f"🛑 Kill signal received for Aria2: {gid}")
                        try: self.aria2.remove([gid], force=True, clean=True)
                        except: pass
                        raise Exception("TASK_CANCELLED_BY_USER")
                
                # Faster refresh rate for smooth UI
                await asyncio.sleep(2)

            # 3. Resolve File Path
            # Refetch one last time to get the final list on disk
            # Refetch to ensure we have the final file list
            download = self.aria2.get_download(gid)
            
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
                self.aria2.remove([gid], force=True, clean=True)
            except: 
                pass
                 
            return str(largest_file)

        except Exception as e:
            logger.error(f"Aria2 Fatal Logic: {e}")
            raise e

downloader = Downloader()