# apps/worker-video/handlers/processor.py
import asyncio
import json
import logging
import os

logger = logging.getLogger("MediaProcessor")

class MediaProcessor:
    """
    Shadow Media Engine:
    Handles local manipulation of video files before upload using FFmpeg/FFprobe.
    
    Responsibilities:
    1. Deep Inspection: Subtitles, Audio Tracks, Resolution.
    2. Asset Generation: Quality Screenshots, Verification Samples.
    """

    def __init__(self):
        # We assume 'ffmpeg' and 'ffprobe' are in the system PATH
        # (Verified: They are installed in the Dockerfile)
        pass

    async def probe(self, file_path: str) -> dict:
        """
        Runs ffprobe to extract technical details for the DB Schema.
        Returns: { duration, width, height, subtitles: [], audio: [] }
        """
        if not os.path.exists(file_path):
            return {}

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            file_path
        ]

        try:
            # 1. Execute FFprobe
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFprobe Non-Zero: {stderr.decode()}")
                # Fallback to defaults
                return {"width": 0, "height": 0, "duration": 0.0, "subtitles": [], "audio": []}

            # 2. Parse JSON Output
            stdout = stdout.decode()
            data = json.loads(stdout)
            format_info = data.get("format", {})
            all_streams = data.get("streams", [])

            # 3. Video Stats
            video_stream = next((s for s in all_streams if s["codec_type"] == "video"), {})

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))

            # --- DETECT 10-BIT ---
            pix_fmt = video_stream.get("pix_fmt", "")
            is_10bit = "10le" in pix_fmt or "10bit" in pix_fmt

            size_bytes = int(format_info.get("size", 0))
            duration = float(format_info.get("duration", 0))

            # 4. Extract Subtitles (For Player Selector)
            # Schema: SubtitleTrack(lang, index)
            subtitles = []
            for track in all_streams:
                if track.get("codec_type") == "subtitle":
                    tags = track.get("tags", {})
                   # Logic: Get clean ISO code and Readable Title
                    lang_code = tags.get("language", "unk")
                    display_title = tags.get("title", lang_code)

                    # Critical for mpv/artplayer Selection
                    subtitles.append({
                        "index": int(track.get("index", 0)),
                        "lang": display_title,  # Store the readable title
                        "code": lang_code    # Store the iso code
                    })

            # 5. Extract Audio (robust parsing)
            audio_tracks = []
            for track in all_streams:
                if track.get("codec_type") == "audio":
                    tags = track.get("tags", {})

                    # Code: und -> Title? -> "unk"
                    code = tags.get("language", "und")
                    title = tags.get("title", "")

                    # Garbage Filter for "Track 1"
                    if code == "und" and title:
                        if any(x in title.lower() for x in ['track', 'sound', 'stereo']):
                            code = "unk"
                        else:
                            code = title[:3] # Use first 3 chars of title as makeshift code

                    audio_tracks.append({
                        "index": int(track.get("index", 0)),
                        "code": code if len(code) < 10 else "unk",
                        "codec": track.get("codec_name", "aac"),
                        "channels": float(track.get("channels", 2.0))
                    })

            logger.info(f"🔍 PROBED: {width}x{height} {'(10-bit)' if is_10bit else ''}, {len(subtitles)} subs, {len(audio_tracks)} audio, {duration}s")

            return {
                "width": width,
                "height": height,
                "is_10bit": is_10bit,
                "size_bytes": size_bytes,
                "duration": duration,
                "subtitles": subtitles,
                "audio": audio_tracks
            }

        except Exception as e:
            logger.error(f"Probe Execution Error: {e}")
            # Return safe zeros so leech.py doesn't crash on format string
            return {
                "width": 0, "height": 0, "size_bytes": 0,
                "duration": 0.0, "subtitles": [], "audio": []
            }

    async def generate_screenshots(self, file_path: str, duration: float, count=3) -> list:
        """
        Generates 3 evenly spaced JPG screenshots for the Website Gallery.
        returns: List of local file paths.
        """
        if duration < 10: return []

        paths = []
        base_name = os.path.splitext(file_path)[0]

        # Calculate timestamps (15%, 50%, 85%)
        percentages = [0.15, 0.50, 0.85]

        # Limit to 3 max to save upload bandwidth
        if count != 3: percentages = [0.50]

        for i, pct in enumerate(percentages):
            timestamp = duration * pct
            out_file = f"{base_name}_screen_{i+1}.jpg"

            # Command: Fast Seek -> Take 1 Frame -> Save as JPG High Quality
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(timestamp),
                "-i", file_path,
                "-vframes", "1",
                "-q:v", "2", # High Quality
                out_file
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()

            if os.path.exists(out_file):
                paths.append(out_file)

        return paths

    async def generate_sample(self, file_path: str, duration: float) -> str:
        """
        Creates a lightweight 30s sample.
        Logic: Try to skip the intro (starts at 5% or 2 mins mark).
        """
        if duration < 60: return None # Too short for sample

        start_time = min(duration * 0.1, 120) # 10% or 2 minutes, whichever is earlier
        out_file = f"{os.path.splitext(file_path)[0]}_sample.mp4"

        # Re-encode specifically for compatibility and file size
        # using 'libx264' + 'ultrafast' for speed
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", file_path,
            "-t", "30",
            "-map", "0:v:0", # Map first video
            "-map", "0:a:0", # Map first audio
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "64k", "-ac", "2",
            out_file
        ]

        logger.info(f"✂️ Cutting Sample at {start_time}s...")
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if os.path.exists(out_file):
            return out_file
        return None

# Singleton Instance
processor = MediaProcessor()
