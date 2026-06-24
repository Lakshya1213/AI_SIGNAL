import os
import json
from src.utils.logger import Logger

class SeenCache:
    def __init__(self, cache_path: str = "outputs/seen_cache.json"):
        self.cache_path = cache_path
        self.seen_urls = set()
        self.load()

    def load(self):
        """
        Load the cache from disk.
        """
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.seen_urls = set(data)
                Logger.info(f"Loaded {len(self.seen_urls)} URLs from seen cache.")
            except Exception as e:
                Logger.warn(f"Failed to load seen cache: {e}. Starting fresh.")
                self.seen_urls = set()
        else:
            # Ensure folder exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            self.seen_urls = set()

    def is_seen(self, url: str) -> bool:
        """
        Check if a URL has already been processed in a previous run.
        """
        if not url:
            return True
        return url.strip() in self.seen_urls

    def add(self, url: str):
        """
        Mark a URL as processed.
        """
        if url:
            self.seen_urls.add(url.strip())

    def save(self):
        """
        Persist the seen URLs cache to disk.
        """
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_urls), f, indent=2)
            Logger.info(f"Persisted seen cache containing {len(self.seen_urls)} URLs.")
        except Exception as e:
            Logger.error(f"Failed to persist seen cache: {e}")
