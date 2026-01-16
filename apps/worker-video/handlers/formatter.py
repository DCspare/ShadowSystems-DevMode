# apps/worker-video/handlers/formatter.py
import logging
import PTN
import os
import re
import urllib.parse
from datetime import timedelta
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class MessageFormatter:
    """
    Design Engine: Transforms raw file data into aesthetic Telegram cards.
    Adheres to the "Shadow Systems" glass style.
    """
    LANG_MAP = {
        'eng': 'English', 'jpn': 'Japanese', 'spa': 'Spanish',
        'fra': 'French', 'ger': 'German', 'ita': 'Italian',
        'rus': 'Russian', 'chi': 'Chinese', 'por': 'Portuguese',
        'hin': 'Hindi', 'kor': 'Korean', 'ara': 'Arabic',
        'unk': 'Unknown', 'und': 'Undefined'
    }
    
    def __init__(self, domain="https://shadow.xyz"):
        # SAFETY : Stripping and Logic Check
        raw_domain = os.getenv("DOMAIN_NAME", "https://shadow.xyz").strip().strip("'").strip('"')
        
        # Enforce HTTPS unless localhost (Potato Mode)
        if "localhost" not in raw_domain and not raw_domain.startswith("https://"):
            raw_domain = f"https://{raw_domain}"
        elif not raw_domain.startswith("http"): 
            raw_domain = f"http://{raw_domain}"
            
        self.domain = raw_domain.rstrip('/')

    def human_size(self, size_in_bytes: int) -> str:
        """Converts bytes to 1.45 GB"""
         # Safety fallback
        if not isinstance(size_in_bytes, (int, float)):
            return "0.00 B"

        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.2f} PB"

    def format_duration(self, seconds: float):
        """Converts 1435s to 00:24:10"""
        if not isinstance(seconds, (int, float)): seconds = 0
        return str(timedelta(seconds=int(seconds))).zfill(8)

    def is_hash_filename(self, filename: str) -> bool:
        """Detects if filename is a mongo/hash id (e.g. 69635eecfedb533e248f61e6)"""
        base = os.path.splitext(filename)[0]
        # Common hash length is 24 (mongo) or 32 (md5) hex chars
        return bool(re.match(r'^[a-fA-F0-9]{20,40}$', base))

    def build_caption(self, tmdb_id, meta, file_name, db_entry=None, episode_meta=None):
        """
        Builds specific formatted card for Shadow Systems V2.
        Ref: Monster 2004 anime example
        
        TASK #30981 COMPLETE
        ANIME or SERIES or MOVIE # according to content 
        NAME: 📁 Monster [2004]
        EPISODE: S01 E04 - "The Executioner"

        ┌ 💿 Res: 1920x1080 (10bit) # or WebDL etc...
        ├ 🔊 Audio: AAC 2.0 (Japanese, English) # all audio formats will be here and in mongoDB as well we need it for our frontend 
        ├ 📝 Subtitles: Soft (English) # or Hindi etc...
        ├ 💾 Size: 1.45 GB
        ├ ⏳ Duration: 00:24:10
        ├ ⭐ Rating: 8.7/10 # from TMDB or MAL according to content 
        └ 🎭 Genre: Thriller, Mystery, Psychology # from TMDB or MAL according to content 
            # all these are also needed in mongoDB for frontend 
        👇 PREVIEW ASSETS
        (Screenshots & Sample attached below)

        #ShadowSystems #Anime 

        [📥 Direct DL](StreamVault_download_URL) | [🎬 Watch Online](StreamVault_PlayerPage_URL) 
        # buttons will be great even if bot is private
        """
        is_hash = self.is_hash_filename(file_name)
       
        # 1. Base Info
        ptn = PTN.parse(file_name) if not is_hash else {}
        
        # Priority: DB Title (Monster) > PTN Title > Filename
        title = db_entry.get('title') if db_entry else ptn.get('title', file_name)
        year = db_entry.get('year') if db_entry else ptn.get('year', '202X')

       # 2. Tag Resolver (Anime/Series/Movie)
        media_type = db_entry.get('media_type', 'movie').upper()
        if "TV" in media_type: media_type = "SERIES"

        # 3. Episode Block (S01 E04 - "Title")
        episode_line = ""
        season = ptn.get('season')
        episode = ptn.get('episode')
        
        if season is not None and episode is not None:
             ep_name = ""
             if episode_meta and episode_meta.get('name'):
                 ep_name = f' - "{episode_meta.get("name")}"' # - "The Executioner"
             
             episode_line = f"EPISODE: S{season:02d} E{episode:02d}{ep_name}"

        # 4. Tech Stats
        width = meta.get('width', 0)
        res_str = "Unknown"
        if width >= 3800: res_str = "4K UHD"
        elif width >= 1900: res_str = "1080p (BluRay)"
        elif width >= 1200: res_str = "720p (HD)"
        elif width > 0: res_str = f"{width}x{meta.get('height')}"

        if meta.get('is_10bit'): res_str += " (10bit)"

        # 5. Audio Formatting
        # Goal: "AAC 2.0 (Japanese, English)"
        audio_text = "Unknown"
        if meta.get('audio'):
            # Group codecs and languages
            first_codec = meta['audio'][0].get('codec', 'aac').upper()
            chan = meta['audio'][0].get('channels', 2.0)
            chan_str = f"{int(chan)}.1" if chan % 1 != 0 else f"{int(chan)}.0"
            
            # Lang list
            langs = []
            for t in meta['audio']:
                l = t.get('code', 'unk')
                readable = self.LANG_MAP.get(l, l.title())
                if readable not in langs: langs.append(readable)
            
            audio_text = f"{first_codec} {chan_str} ({', '.join(langs)})"

        # 6. Ratings / Genres
        rating = str(round(db_entry.get('rating', 0.0), 1)) if db_entry else "N/A"
        
        g_list = db_entry.get('genres', [])
        if not g_list: g_list = ['Uncategorized']
        genres = ", ".join(g_list[:3]) # Limit 3

        # 7. Subtitles
        sub_text = "None"
        if meta.get('subtitles'):
             # Logic to highlight ENG
             eng = any('eng' in s['code'].lower() for s in meta['subtitles'])
             display = "English" if eng else meta['subtitles'][0]['lang']
             plus = len(meta['subtitles']) - 1 if eng else len(meta['subtitles'])
             if plus > 0: display += f" +{plus} others"
             sub_text = f"Soft ({display})"

        # --- THE FINAL BLOCK ---
        # Logic: If no Episode line, omit that row.

        layout = f"""
**TASK #{tmdb_id} COMPLETE**

**NAME:** `📁 {title} [{year}]`
{f"**{episode_line}**" if episode_line else ""}

┌ 💿 **Res:** `{res_str}`
├ 🔊 **Audio:** `{audio_text}`
├ 📝 **Subtitles:** `{sub_text}`
├ 💾 **Size:** `{self.human_size(meta.get('size_bytes', 0))}`
├ ⏳ **Duration:** `{self.format_duration(meta.get('duration', 0))}`
├ ⭐ **Rating:** `{rating}/10`
└ 🎭 **Genre:** `{genres}`

👇 **PREVIEW ASSETS**
*(Screenshots & Sample attached below)*

#ShadowSystems #{media_type.title()}
"""
        return layout.strip()

    def build_buttons(self, short_id: str):
        """Generates Buttons: Watch Online | Direct DL
           Automatically cleans short_id and ensures strict URL validity.
        """
        if not short_id: return None
        
        # Ensure short_id is url safe
        safe_id = urllib.parse.quote(str(short_id))
        url = f"{self.domain}/view/{safe_id}"

        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 Direct DL", url=url),
                InlineKeyboardButton("🎬 Watch Online", url=url)
            ]
        ])

formatter = MessageFormatter(os.getenv("DOMAIN_NAME", "https://shadowsystems.xyz"))
