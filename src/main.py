import argparse
import os
import sys
from dotenv import load_dotenv
from src.entity_resolution.resolver import EntityResolver
from src.llm.llm_orchestrator import LLMOrchestrator
from src.crawlers.startup_crawler import StartupCrawler
from src.crawlers.product_crawler import ProductCrawler
from src.crawlers.paper_crawler import PaperCrawler
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.job_crawler import JobCrawler
from src.storage.export_csv import export_to_excel
from src.utils.seen_cache import SeenCache
from src.utils.logger import Logger

def main():
    # Load environment variables from .env
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="GraphOne Venture Ecosystem Data Intelligence Pipeline")
    parser.add_argument(
        "--limit", 
        type=int, 
        default=1000, 
        help="Target record count for startups, products, and papers (default: 1000)"
    )
    parser.add_argument(
        "--mock", 
        action="store_true", 
        help="Use rule-based local parser (mock LLM mode) to avoid API call costs and limits"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="outputs/graphone_data.xlsx", 
        help="Path to save the resulting Excel file"
    )
    args = parser.parse_args()

    Logger.info("=========================================")
    Logger.info("Starting GraphOne Data Intelligence Ingestion Pipeline")
    Logger.info(f"Target count limit per category: {args.limit}")
    Logger.info(f"LLM mode: {'MOCK (rule-based local extraction)' if args.mock else 'PRODUCTION (fallback chain API)'}")
    Logger.info("=========================================")

    # Initialize resolver, seen cache, and orchestrator
    resolver = EntityResolver()
    seen_cache = SeenCache()
    orchestrator = LLMOrchestrator(use_mock=args.mock)

    # 1. Startups Crawler
    startup_crawler = StartupCrawler(resolver=resolver)
    startups = startup_crawler.crawl(limit=args.limit)
    
    # Re-fetch raw startups to pass to product crawler
    # This prevents the crawler from doing redundant network requests
    raw_companies = startup_crawler.fetch_raw_startups()

    # 2. Products Crawler
    product_crawler = ProductCrawler(orchestrator=orchestrator, resolver=resolver)
    products = product_crawler.crawl_products(raw_companies, limit=args.limit)

    # 3. Research Papers Crawler
    paper_crawler = PaperCrawler(use_mock=args.mock)
    papers = paper_crawler.crawl(limit=args.limit)

    # 4. News Crawler
    news_crawler = NewsCrawler(cache=seen_cache)
    news = news_crawler.crawl()

    # 5. Job Crawler
    job_crawler = JobCrawler(resolver=resolver, orchestrator=orchestrator, cache=seen_cache)
    jobs = job_crawler.crawl()

    # 6. Get Entity Resolution Log
    mapping_log = resolver.get_mapping_log()

    # Summary
    Logger.info("=========================================")
    Logger.info("Pipeline Statistics:")
    Logger.info(f" - Canonical Startups: {len(startups)}")
    Logger.info(f" - Canonical Products: {len(products)}")
    Logger.info(f" - Research Papers:    {len(papers)}")
    Logger.info(f" - Fresh Jobs (24h):   {len(jobs)}")
    Logger.info(f" - Fresh News (24h):   {len(news)}")
    Logger.info(f" - Entities Resolved:  {len(mapping_log)}")
    Logger.info("=========================================")

    # Export to Excel
    export_to_excel(
        startups=startups,
        products=products,
        papers=papers,
        jobs=jobs,
        news=news,
        mapping_log=mapping_log,
        output_path=args.output
    )
    
    # Save the updated seen cache to disk
    seen_cache.save()
    
    Logger.success("Ingestion pipeline run completed successfully.")

if __name__ == "__main__":
    main()
