# apps/manager/services/metadata.py 
import os
import aiohttp
import logging
from shared.settings import settings

logger = logging.getLogger("Metadata")

class MetadataService:
    def __init__(self):
        # Fallback to os.getenv if settings object isn't fully loaded
        self.api_key = getattr(settings, 'TMDB_API_KEY', os.getenv('TMDB_API_KEY'))
        self.base_url = "https://api.themoviedb.org/3"

    async def search_tmdb(self, query: str, media_type: str = "movie"):
        endpoint = f"{self.base_url}/search/{media_type}"
        params = {"api_key": self.api_key, "query": query, "language": "en-US"}
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                data = await response.json()
                return data.get("results", [])

    async def get_details(self, tmdb_id: int, media_type: str = "movie"):
        endpoint = f"{self.base_url}/{media_type}/{tmdb_id}"
        params = {"api_key": self.api_key, "language": "en-US"}
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status != 200:
                    return None
                return await response.json()

metadata_service = MetadataService()
