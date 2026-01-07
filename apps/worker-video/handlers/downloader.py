import os
import asyncio
import logging
import yt_dlp
import aria2p
from tenacity import retry, stop_after_attempt, wait_fixed

# Initialize logging
logger = logging.getLogger("Downloader")

class Downloader:
    """
    Manages the interaction between yt-dlp (URL extraction)
    and Aria2 (Heavy downloading via RPC).
    """
    def __init__(self, download_path="/app/downloads"):
        self.download_path = download_path
        self.aria2 = None
        
        # Ensure download directory exists
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)

    async def initialize(self):
        """
        Connects to the local Aria2 RPC daemon.
        Assumes 'aria2c --enable-rpc' is already running in background.
        """
        try:
            # Connect to local instance (localhost:6800)
            self.aria2 = aria2p.API(
                aria2p.Client(
                    host="http://localhost",
                    port=6800,
                    secret=""
                )
            )
            logger.info("✅ Connected to Aria2 Daemon")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Aria2: {e}")
            raise e

    def get_direct_url(self, url: str) -> dict:
        """
        Uses yt-dlp to extract the raw video URL or Magnet link.
        Returns a dict with 'url' and 'filename' (if guessable).
        """
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'cookiefile': os.getenv("COOKIES_FILE_PATH", "/app/cookies.txt")
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Analyzing URL with yt-dlp: {url}")
                info = ydl.extract_info(url, download=False)
                
                # If it's a playlist or video, return the raw stream URL
                return {
                    "url": info.get('url') or url, # Direct video link
                    "title": info.get('title', 'Unknown_Video')
                }
        except Exception as e:
            logger.warning(f"yt-dlp failed, assuming direct link or magnet: {e}")
            # Fallback: Just try adding the URL directly to Aria2
            return {"url": url, "title": "Direct_Link"}

    async def start_download(self, raw_link: str) -> str:
        """
        Adds task to Aria2 and monitors until completion.
        Returns: The absolute path of the downloaded file.
        """
        if not self.aria2:
            await self.initialize()

        logger.info(f"Adding to Aria2 queue: {raw_link[:50]}...")
        
        # Add the URI to Aria2
        # options: dir is the download folder
        download = self.aria2.add_uris([raw_link], options={'dir': self.download_path})
        
        # Loop to monitor progress
        while not download.is_complete:
            # Refresh status from daemon
            download.update()
            
            if download.status == 'error':
                logger.error(f"Aria2 Error: {download.error_message}")
                raise Exception("Download failed in Aria2")
                
            # Log progress every 5 seconds (roughly)
            logger.info(f"⬇️ {download.progress_string()} | Speed: {download.download_speed_string()}")
            await asyncio.sleep(2)

        # Download complete
        final_path = str(download.files[0].path)
        logger.info(f"✅ Download Finished: {final_path}")
        
        # Aria2 sometimes keeps files 'locked'. Purge the task record.
        self.aria2.remove([download])
        
        return final_path

# Export a single instance if needed, or instantiate in worker
downloader = Downloader()
