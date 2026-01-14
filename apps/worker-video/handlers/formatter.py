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

    def build_caption(self, tmdb_id, meta, file_name, db_entry=None):
        is_hash = self.is_hash_filename(file_name)
        """
        Constructs the Final Message String.
        db_entry: Optional dict from MongoDB containing Genres/Rating/Year
        meta: Output from processor.probe()
        """
        # 1. Resolve Title
        title = "Unknown"
        year = "202X"
        ptn = {}
        if not is_hash:
            ptn = PTN.parse(file_name)
        
        if db_entry:
            title = db_entry.get('title', title)
            year = db_entry.get('year', year)
        elif not is_hash:
            title = ptn.get('title', file_name)

        quality = ptn.get('quality', 'HD')

        # 2. Get DB Details
        # Handle 'rating' vs 'vote_average' and N/A fallbacks
        rating = "0.0"
        genres = "N/A"
        if db_entry:
            v = db_entry.get('vote_average')
            if v: rating = str(round(float(v), 1))
            g_list = db_entry.get('genres', [])
            if g_list: genres = ", ".join(g_list[:3])

        genres_list = db_entry.get('genres', []) if db_entry else ['Uncategorized']
        if not isinstance(genres_list, list): genres_list = [str(genres_list)]
        genres = ", ".join(genres_list[:3]) # Limit to 3 tags

        # 3. Process Audio & Subs string
        # Ex: "AAC 2.0 (JPN, ENG)"
        audio_line = "Unknown"
        if meta.get('audio'):
            # Collect unique codes first
            langs_found = []
            codec = meta['audio'][0].get('codec', 'aac').upper()
            channels = meta['audio'][0].get('channels', 2.0)
            
            # Use 5.1 formatting
            chan_str = f"{channels:.1f}" if channels % 1 != 0 else f"{int(channels)}.0"

            for t in meta['audio']:
                code = t.get('code', 'unk').lower()
                name = self.LANG_MAP.get(code, code.title())
                if name not in langs_found: langs_found.append(name)
            
            audio_line = f"{codec} {chan_str} ({', '.join(langs_found)})"

        # 4. Smart Subtitles (Goal: "Soft (English)")
        sub_line = "None"
        subs = meta.get('subtitles', [])
        if subs:
            # We assume mkv text subs are "Soft"
            eng_sub = False
            others = 0
            
            for sub_line in subs:
                code = sub_line.get('code', '').lower()
                if 'eng' in code or 'en' == code: eng_sub = True
                else: others += 1
            
            display = "English" if eng_sub else subs[0].get('lang', 'Unknown')
            if others > 0 and not eng_sub: display += f" +{others}"
            elif others > 0 and eng_sub: display = "English" # Prioritize just showing English if present
            
            sub_line = f"Soft ({display})"

        # 5. Header (S01 E04)
        header_block = f"**NAME:** `📁 {title} [{year}]`"

        # NOTE: Hash files can't provide S/E info naturally. 
        # Only valid PTN filenames can.
        if not is_hash:
            season = ptn.get('season')
            episode = ptn.get('episode')
            ep_title = ptn.get('episodeName', '') # PTN sometimes catches title
            
            if isinstance(season, int) and isinstance(episode, int):
                ep_str = f"S{season:02d} E{episode:02d}"
                if ep_title: ep_str += f' - "{ep_title}"'
                header_block += f"\n**EPISODE:** `{ep_str}`"
        
        # 6. Technicals
        res_str = f"{meta.get('width',0)}x{meta.get('height',0)}"
        if meta.get('is_10bit'): res_str += " (10bit)"

        caption = f"""
**TASK #{tmdb_id} COMPLETE**
{header_block}

├ 💿 **Res:** `{res_str}`
├ 🔊 **Audio:** `{audio_line}`
├ 📝 **Subtitles:** `{sub_line}`
├ 💾 **Size:** `{self.human_size(meta.get('size_bytes', 0))}`
├ ⏳ **Duration:** `{self.format_duration(meta.get('duration', 0))}`
├ ⭐ **Rating:** `{rating}/10`
└ 🎭 **Genre:** `{genres}`

👇 **PREVIEW ASSETS**
*(Screenshots & Sample attached below)*

#ShadowSystems #Quality
"""
        return caption.strip()

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
