import asyncio
import aiohttp
from typing import List, Optional
from src.utils.logger import Logger

async def fetch_url_async(session: aiohttp.ClientSession, url: str, headers: dict = None, timeout: int = 12) -> Optional[str]:
    """
    Asynchronously fetch a single URL text response.
    """
    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                return await response.text()
            else:
                Logger.warn(f"Async fetch failed for {url}. HTTP Code: {response.status}")
                return None
    except Exception as e:
        Logger.warn(f"Async exception fetching {url}: {e}")
        return None

async def fetch_all_urls_async(urls: List[str], headers: dict = None, max_concurrency: int = 10) -> List[Optional[str]]:
    """
    Asynchronously fetch a list of URLs concurrently with a host limit.
    """
    # Restrict concurrent connections to prevent aggressive hitting
    connector = aiohttp.TCPConnector(limit_per_host=max_concurrency)
    timeout = aiohttp.ClientTimeout(total=15)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for url in urls:
            tasks.append(fetch_url_async(session, url, headers))
        
        # Run all requests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Clean results (exceptions will be returned, convert them to None)
        clean_results = []
        for r in results:
            if isinstance(r, Exception) or r is None:
                clean_results.append(None)
            else:
                clean_results.append(r)
        return clean_results
