import os
import asyncio
import logging
import yt_dlp
import aria2p

logger = logging.getLogger("Downloader")

class Downloader:
    def __init__(self, download_path="/app/downloads"):
        self.download_path = download_path
        self.aria2 = None
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)

    async def initialize(self):
        try:
            self.aria2 = aria2p.API(
                aria2p.Client(host="http://localhost", port=6800, secret="")
            )
            logger.info("✅ Connected to Aria2 Daemon")
        except Exception:
            self.aria2 = None

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            # Print log only every 10% roughly (to reduce spam) or based on a timer
            # Here we trust d.get('_percent_str') string provided by yt-dlp
            # We strip ANSI color codes just in case
            pct = d.get('_percent_str', '0%').replace('\x1b[0;94m', '').replace('\x1b[0m', '').strip()
            
            # A simplistic deduplicator can be done by parsing string value or time
            # For Docker logs, we will accept the spam but label it clearly:
            # logger.info(f"⬇️ Native: {pct}")
            # NOTE: Logging every chunk will flood terminal. We print to stdout with flush? 
            # Better strategy: Python doesn't buffer stderr if configured well. 
            pass

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
                return {
                    "url": info.get('url'), 
                    "filename": f"{info.get('title')}.{info.get('ext')}",
                    "type": "video_site"
                }
        except:
            filename = url.split("/")[-1].split("?")[0]
            if not filename: filename = "video.mp4"
            return {"url": url, "filename": filename, "type": "raw"}

    def _native_logger_progress(self, d):
        """Dedicated hook to make yt-dlp logs visible in Docker"""
        if d['status'] == 'downloading':
            # Extract clean percentage
            try:
                raw_pct = d.get('_percent_str', '0%').strip()
                # Remove ANSI colors just in case
                clean_pct = raw_pct.replace('%','').split('.')[0]
                pct_val = int(clean_pct)
                
                # Check our internal tracker to avoid spam
                # Using a class attribute via 'self' is tricky in a hook passed to library
                # So we use a simple modulus strategy logic which is robust
                
                if pct_val % 20 == 0 and pct_val > 0:
                     # Only log if we haven't logged this specific integer recently? 
                     # For Docker simpler is better. Spam is better than silence.
                     print(f"⬇️ [DL] {raw_pct} | {d.get('_speed_str')} | ETA {d.get('_eta_str')}", flush=True)
                     
            except:
                pass # Don't crash on log formatting
        
        elif d['status'] == 'finished':
            print("✅ [DL] Download Phase Complete. Finalizing...", flush=True)

    async def start_download(self, target: dict) -> str:
        raw_link = target['url']
        final_path = os.path.join(self.download_path, target.get('filename', 'dl.mp4'))

        # Magnet -> Aria2
        if raw_link.startswith("magnet:"):
            return await self.download_with_aria2(raw_link)

        # HTTPS -> Native
        logger.info(f"🌐 Mode: Native HTTP")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': f"{self.download_path}/%(title)s.%(ext)s",
                'nocheckcertificate': True,
                # HOOK THE LOGGER
                'progress_hooks': [self._native_logger_progress],
                'quiet': True, 
                'no_warnings': True
            }
            # Custom overwrite for raw
            if target.get('type') == 'raw':
                ydl_opts['outtmpl'] = final_path

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._native_run(raw_link, ydl_opts))
            
            # Resolve exact filename created
            if os.path.exists(final_path): return final_path
            
            # Fuzzy match finder if name changed
            potential_name = final_path.rsplit('.', 1)[0]
            for f in os.listdir(self.download_path):
                if potential_name in f or target.get('filename') in f:
                    return os.path.join(self.download_path, f)
            return final_path # Hope

        except Exception as e:
            logger.error(f"DL Failed: {e}")
            raise e

    def _native_run(self, url, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def download_with_aria2(self, raw_link):
        if not self.aria2: await self.initialize()
        logger.info("🧲 Sending to Aria2...")
        try:
            dl = self.aria2.add_uris([raw_link], options={'dir': self.download_path})
            while not dl.is_complete:
                dl.update()
                if dl.status == 'error': raise Exception(dl.error_message)
                # Aria2 logging
                if int(dl.completed_length / max(dl.total_length, 1) * 100) % 20 == 0:
                     logger.info(f"🧲 Aria2: {dl.progress_string()}")
                await asyncio.sleep(2)
            return str(dl.files[0].path)
        except Exception as e:
            raise e

downloader = Downloader()
