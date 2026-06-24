import sys
import os
# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from typing import List, Dict, Any
from src.schemas.product_schema import ProductEntity, PricingModel
from src.llm.llm_orchestrator import LLMOrchestrator
from src.entity_resolution.resolver import EntityResolver
from src.utils.logger import Logger

class ProductCrawler:
    def __init__(self, orchestrator: LLMOrchestrator, resolver: EntityResolver):
        self.orchestrator = orchestrator
        self.resolver = resolver

    def crawl_products(self, raw_companies: List[Dict[str, Any]], limit: int = 1000) -> List[ProductEntity]:
        """
        Process YC companies into ProductEntities by extracting pricing models via the LLM orchestrator.
        """
        # Filter for active companies with websites (same as startup crawler)
        active_companies = [
            c for c in raw_companies 
            if c.get("status") == "Active" and c.get("website")
        ]
        
        target_companies = active_companies[:limit]
        Logger.info(f"Extracting product records from first {len(target_companies)} companies...")

        products = []
        for i, c in enumerate(target_companies):
            name = c.get("name", "")
            description = c.get("long_description") or c.get("one_liner") or ""
            website = c.get("website", "")
            tags = c.get("tags", [])
            source_url = c.get("url") or f"https://www.ycombinator.com/companies/{c.get('slug')}"

            # Step 1: Run LLM extraction or Mock extraction
            extracted = self.orchestrator.extract_startup_product(
                name=name,
                description=description,
                website=website,
                tags=tags
            )

            # Step 2: Canonicalize startup name
            raw_startup = extracted.get("canonical_startup_name") or name
            canonical_startup = self.resolver.resolve_startup(raw_startup)

            # Step 3: Parse Pricing Model
            pricing_str = extracted.get("pricing_model") or "FREEMIUM"
            try:
                pricing_model = PricingModel(pricing_str.upper())
            except ValueError:
                pricing_model = PricingModel.FREEMIUM

            product_name = extracted.get("primary_product_name") or canonical_startup

            entity = ProductEntity(
                source_name="Y Combinator",
                source_url=source_url,
                startup_name=canonical_startup,
                pricing_model=pricing_model,
                product_name=product_name
            )
            products.append(entity)

            if (i + 1) % 100 == 0:
                Logger.info(f"Extracted {i + 1}/{len(target_companies)} products...")

        Logger.success(f"Successfully processed {len(products)} canonical Product records.")
        return products
