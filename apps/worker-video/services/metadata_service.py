import logging
import re

import aiohttp

logger = logging.getLogger("MetadataService")


class MetadataService:
    def __init__(self, tmdb_api_key: str):
        self.tmdb_api_key = tmdb_api_key

    def sanitize_url(self, url):
        """Removes api_key from logs
        Usage: {self.sanitize_url(url)}
        """
        if "api_key=" in url:
            return url.split("api_key=")[0] + "api_key=***HIDDEN***"
        return url

    def _format_duration(self, minutes: int):
        if not minutes:
            return "N/A"
        if minutes < 60:
            return f"{minutes}m"
        return f"{minutes // 60}h {minutes % 60}m"

    def _format_currency(self, amount: int):
        if not amount:
            return "N/A"
        return f"${amount:,.0f}"

    def _extract_yt_key(self, url: str):
        if not url:
            return None
        # Extracts ID from various YT formats including embed links
        match = re.search(
            r"(?:embed/|v=|v/|youtu\.be/|/v/|/e/|watch\?v=|&v=)([\w-]{11})", url
        )
        return match.group(1) if match else None

    async def fetch_jikan_anime(self, mal_id: int):
        """Deep fetch for Anime using /full, /characters, and /videos"""
        async with aiohttp.ClientSession() as sess:
            # 1. Full Data
            async with sess.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/full"
            ) as resp:
                if resp.status != 200:
                    return None
                res = await resp.json()
                d = res["data"]
                if not d.get("approved"):
                    return None

                # 2. Relations Mapping
                relations = []
                for rel in d.get("relations", []):
                    relations.append(
                        {
                            "relation": rel["relation"],
                            "entry": [
                                {
                                    "mal_id": e["mal_id"],
                                    "name": e["name"],
                                    "type": e["type"],
                                }
                                for e in rel["entry"]
                            ],
                        }
                    )

                # 3. Characters & VAs (Max 5)
                cast = []
                async with sess.get(
                    f"https://api.jikan.moe/v4/anime/{mal_id}/characters"
                ) as c_resp:
                    if c_resp.status == 200:
                        c_data = (await c_resp.json())["data"]
                        for item in c_data[:5]:
                            va = item["voice_actors"][0] if item["voice_actors"] else {}
                            cast.append(
                                {
                                    "name": item["character"]["name"],
                                    "image": item["character"]["images"]["jpg"][
                                        "image_url"
                                    ],
                                    "va_name": va.get("person", {}).get("name"),
                                    "va_image": va.get("person", {})
                                    .get("images", {})
                                    .get("jpg", {})
                                    .get("image_url")
                                    if va
                                    else None,
                                }
                            )

                # 4. Enhanced Trailer Check (Promo Embed vs Trailer Key)
                trailer_key = d.get("trailer", {}).get("youtube_id")
                if not trailer_key:
                    # Check promo videos endpoint if main trailer is missing
                    async with sess.get(
                        f"https://api.jikan.moe/v4/anime/{mal_id}/videos"
                    ) as v_resp:
                        if v_resp.status == 200:
                            v_data = await v_resp.json()
                            promo = v_data["data"].get("promo", [])
                            if promo:
                                trailer_key = self._extract_yt_key(
                                    promo[0].get("trailer", {}).get("embed_url")
                                )

                return {
                    "mal_id": mal_id,
                    "media_type": "anime",
                    "title": d.get("title_english") or d.get("title"),
                    "titles": {
                        "english": d.get("title_english"),
                        "japanese": d.get("title_japanese"),
                        "synonyms": d.get("title_synonyms", []),
                    },
                    "year": str(
                        d.get("year")
                        or d.get("aired", {})
                        .get("prop", {})
                        .get("from", {})
                        .get("year")
                        or ""
                    ),
                    "airing_status": d.get("status"),
                    "duration": d.get("duration"),  # "23 min per ep"
                    "rating": float(d.get("score") or 0.0),
                    "age_rating": d.get("rating"),  # e.g., "R - 17+"
                    "overview": d.get("synopsis"),  # Synopsis used as overview
                    "rank": d.get("rank"),
                    "season_name": d.get("season"),
                    "broadcast": d.get("broadcast", {}).get("string"),
                    "source": d.get("source"),
                    "demographics": [dm["name"] for dm in d.get("demographics", [])],
                    "themes": [t["name"] for t in d.get("themes", [])],
                    "genres": [g["name"] for g in d.get("genres", [])],
                    "studios": [s["name"] for s in d.get("studios", [])],
                    "relations": relations,
                    "cast": cast,
                    "visuals": {
                        "poster": d["images"]["jpg"]["large_image_url"],
                        "trailer_key": trailer_key,
                    },
                }

    async def fetch_tmdb_movie(self, movie_id: int):
        """Strict Movie Call"""
        async with aiohttp.ClientSession() as sess:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={self.tmdb_api_key}&append_to_response=videos"
            async with sess.get(url) as resp:
                if resp.status != 200:
                    return None
                d = await resp.json()

                # 1. Multi-Trailer Logic (Max 2)
                videos = d.get("videos", {}).get("results", [])
                trailers = [
                    v["key"]
                    for v in videos
                    if v["type"] in ["Trailer", "Teaser", "Clip"]
                    and v["site"] == "YouTube"
                ]

                # Detect Anime Movie
                is_ani = (
                    any(g["name"] == "Animation" for g in d.get("genres", []))
                    and d.get("original_language") == "ja"
                )

                return {
                    "tmdb_id": movie_id,
                    "imdb_id": d.get("imdb_id"),
                    "media_type": "anime_movie" if is_ani else "movie",
                    "title": d.get("title"),
                    "year": (d.get("release_date") or "")[:4],
                    "airing_status": d.get("status"),  # "Released"
                    "popularity": round(d.get("popularity", 0.0), 1),
                    "rating": round(d.get("vote_average", 0.0), 1),
                    "release_date": d.get("release_date"),
                    "runtime": self._format_duration(d.get("runtime")),
                    "budget": self._format_currency(d.get("budget")),
                    "revenue": self._format_currency(d.get("revenue")),
                    "tagline": d.get("tagline"),
                    "genres": [g["name"] for g in d.get("genres", [])],
                    "overview": d.get("overview"),
                    "visuals": {
                        "poster": f"https://image.tmdb.org/t/p/w500{d.get('poster_path')}",
                        "backdrop": f"https://image.tmdb.org/t/p/original{d.get('backdrop_path')}",
                        "trailer_keys": trailers[:2],  # Stores up to 2 keys
                    },
                }

    async def fetch_tmdb_tv(self, tv_id: int):
        """Strict TV Call"""
        async with aiohttp.ClientSession() as sess:
            url = f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={self.tmdb_api_key}&append_to_response=videos"
            async with sess.get(url) as resp:
                if resp.status != 200:
                    return None
                d = await resp.json()

                # 1. Multi-Trailer Logic (Max 2)
                videos = d.get("videos", {}).get("results", [])
                trailers = [
                    v["key"]
                    for v in videos
                    if v["type"] in ["Trailer", "Teaser", "Behind the Scenes"]
                    and v["site"] == "YouTube"
                ]

                return {
                    "tmdb_id": tv_id,
                    "media_type": "tv",
                    "title": d.get("name"),
                    "year": (d.get("first_air_date") or "")[:4],
                    "airing_status": d.get("status"),  # "Returning Series"
                    "in_production": d.get("in_production"),  # true false
                    "popularity": round(d.get("popularity", 0.0), 1),
                    "rating": round(d.get("vote_average", 0.0), 1),
                    "episode_run_time": f"{d.get('episode_run_time')[0]}m"
                    if d.get("episode_run_time")
                    else "N/A",
                    "first_air_date": d.get("first_air_date"),
                    "last_air_date": d.get("last_air_date"),
                    "total_episodes": d.get("number_of_episodes"),
                    "total_seasons": d.get("number_of_seasons"),
                    "created_by": [p["name"] for p in d.get("created_by", [])],
                    "genres": [g["name"] for g in d.get("genres", [])],
                    "overview": d.get("overview"),
                    "tagline": d.get("tagline"),
                    "visuals": {
                        "poster": f"https://image.tmdb.org/t/p/w500{d.get('poster_path')}",
                        "backdrop": f"https://image.tmdb.org/t/p/original{d.get('backdrop_path')}",
                        "trailer_keys": trailers[:2],
                    },
                }

    async def fetch_anime_episode_meta(self, mal_id: int, ep_num: int):
        """Fetches detailed episode data for Anime"""
        async with aiohttp.ClientSession() as sess:
            # 1. Fetch Episode Info
            async with sess.get(
                f"https://api.jikan.moe/v4/anime/{mal_id}/episodes/{ep_num}"
            ) as resp:
                if resp.status != 200:
                    return {}
                d = (await resp.json())["data"]

                # 2. Fetch Still Image (From videos endpoint)
                still = None
                async with sess.get(
                    f"https://api.jikan.moe/v4/anime/{mal_id}/videos"
                ) as v_resp:
                    if v_resp.status == 200:
                        v_data = (await v_resp.json())["data"].get("episodes", [])
                        # Match the episode number
                        for ep_vid in v_data:
                            if ep_vid.get("mal_id") == ep_num:
                                still = (
                                    ep_vid.get("images", {})
                                    .get("jpg", {})
                                    .get("image_url")
                                )
                                break

                return {
                    "episode": ep_num,
                    "title": d.get("title"),
                    "title_japanese": d.get("title_japanese"),
                    "title_romanji": d.get("title_romanji"),
                    "aired": d.get("aired"),
                    "score": d.get("score"),
                    "filler": d.get("filler"),
                    "recap": d.get("recap"),
                    "synopsis": d.get("synopsis"),
                    "still_path": still,
                }

    async def fetch_show_episode_meta(self, tmdb_id: int, s_num: int, e_num: int):
        """Fetches details for a Specific Episode Title with enhanced logging"""
        if not self.tmdb_api_key or s_num == 0 or e_num == 0:
            return None

        try:
            url = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{s_num}/episode/{e_num}?api_key={self.tmdb_api_key}"
            logger.info(f"🔎 Checking Episode Metadata: {self.sanitize_url(url)}")

            async with aiohttp.ClientSession() as sess:
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        ep_data = await resp.json()
                        title = ep_data.get("name")
                        logger.info(f"✅ Found Ep Title: {title}")
                        return {
                            "name": ep_data.get("name"),
                            "overview": ep_data.get("overview"),
                            "runtime": ep_data.get("runtime"),
                            "still_path": ep_data.get("still_path"),
                        }
                    else:
                        logger.warning(f"❌ TMDB Ep Error {resp.status}")
        except Exception as e:
            logger.error(f"Episode fetch failed: {e}")
        return None
