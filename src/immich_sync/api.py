import aiohttp
import asyncio


class ImmichAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers_json = {"Accept": "application/json", "x-api-key": api_key}
        self.headers_octo = {"Accept": "application/octet-stream", "x-api-key": api_key}

    async def list_albums(self, session: aiohttp.ClientSession, shared: bool = False):
        url = f"{self.base_url}/api/albums"
        if shared:
            url += "?shared=true"
        async with session.get(url, headers=self.headers_json) as r:
            r.raise_for_status()
            return await r.json()

    async def get_album(self, session: aiohttp.ClientSession, album_id: str):
        url = f"{self.base_url}/api/albums/{album_id}"
        async with session.get(url, headers=self.headers_json) as r:
            r.raise_for_status()
            return await r.json()

    async def fetch_asset_info(
        self,
        session: aiohttp.ClientSession,
        asset_id: str,
        semaphore: asyncio.Semaphore,
        num_retries: int = 3,
        backoff_factor: int = 1,
    ):
        async with semaphore:
            for i in range(num_retries):
                try:
                    url = f"{self.base_url}/api/assets/{asset_id}"
                    async with session.get(url, headers=self.headers_json) as r:
                        r.raise_for_status()
                        return await r.json()
                except Exception:
                    if i < num_retries - 1:
                        await asyncio.sleep(backoff_factor * 2**i)
                    else:
                        raise

    async def fetch_asset_size(
        self,
        session: aiohttp.ClientSession,
        asset_id: str,
        semaphore: asyncio.Semaphore,
        num_retries: int = 3,
        backoff_factor: int = 1,
    ):
        async with semaphore:
            for i in range(num_retries):
                try:
                    url = f"{self.base_url}/api/assets/{asset_id}/original"
                    async with session.head(url, headers=self.headers_octo) as r:
                        r.raise_for_status()
                        return int(r.headers.get("Content-Length", 0))
                except Exception:
                    if i < num_retries - 1:
                        await asyncio.sleep(backoff_factor * 2**i)
                    else:
                        raise
