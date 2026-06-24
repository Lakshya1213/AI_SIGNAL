import requests
from typing import List, Dict, Any
import sys
import os
# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.schemas.startup_schema import StartupEntity
from src.entity_resolution.resolver import EntityResolver
from src.utils.logger import Logger

class StartupCrawler:
    def __init__(self, resolver: EntityResolver):
        self.url = "https://yc-oss.github.io/api/companies/all.json"
        self.resolver = resolver

    def fetch_raw_startups(self) -> List[Dict[str, Any]]:
        """
        Fetch the raw company records from the YC OSS database.
        """
        Logger.info(f"Fetching YC startups from {self.url}...")
        try:
            r = requests.get(self.url, timeout=20)
            if r.status_code == 200:
                data = r.json()
                Logger.info(f"Fetched {len(data)} raw company records.")
                return data
            else:
                Logger.error(f"Failed to fetch YC companies. Code: {r.status_code}")
                return []
        except Exception as e:
            Logger.error(f"Exception during fetching YC companies: {e}")
            return []

    def crawl(self, limit: int = 1000) -> List[StartupEntity]:
        """
        Process YC startups into canonical StartupEntities.
        """
        raw_companies = self.fetch_raw_startups()
        if not raw_companies:
            return []

        # Filter for active companies with websites
        active_companies = [
            c for c in raw_companies 
            if c.get("status") == "Active" and c.get("website")
        ]
        Logger.info(f"Filtered to {len(active_companies)} active startups.")

        # Limit to the requested size
        target_companies = active_companies[:limit]
        Logger.info(f"Processing first {len(target_companies)} startups...")

        startups = []
        for c in target_companies:
            raw_name = c.get("name", "")
            # Resolve/canonicalize the startup name
            canonical_name = self.resolver.resolve_startup(raw_name)
            
            # Map team_size to employee_count
            employee_count = c.get("team_size")
            if employee_count is not None:
                try:
                    employee_count = int(employee_count)
                except ValueError:
                    employee_count = None

            source_url = c.get("url") or f"https://www.ycombinator.com/companies/{c.get('slug')}"

            entity = StartupEntity(
                source_name="Y Combinator",
                source_url=source_url,
                entity_name=canonical_name,
                employee_count=employee_count
            )
            startups.append(entity)

        Logger.success(f"Successfully processed {len(startups)} canonical Startup records.")
        return startups
