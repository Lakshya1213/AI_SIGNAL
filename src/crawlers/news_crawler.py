import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
import re
import asyncio
from typing import List, Dict, Any, Optional
import sys
import os

# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.schemas.news_schema import NewsEntity
from src.utils.seen_cache import SeenCache
from src.utils.async_http import fetch_all_urls_async
from src.utils.logger import Logger

class NewsCrawler:
    def __init__(self, cache: SeenCache = None):
        self.cache = cache or SeenCache()
        self.sources = {
            "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
            "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
            "Nvidia Blog": "https://blogs.nvidia.com/feed/",
            "AWS ML Blog": "https://aws.amazon.com/blogs/machine-learning/feed/",
            "KDnuggets": "https://www.kdnuggets.com/feed"
        }
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def parse_rss_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse common RSS publication date formats into UTC datetime.
        """
        if not date_str:
            return None
        date_str = date_str.strip()
        
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except ValueError:
                continue
                
        try:
            clean_str = re.sub(r'\b(GMT|UTC|EDT|PDT|EST|PST)\b', '+0000', date_str).strip()
            dt = datetime.strptime(clean_str, "%a, %d %b %Y %H:%M:%S %z")
            return dt.astimezone(timezone.utc)
        except Exception:
            pass
            
        return None

    def clean_html_to_paragraphs(self, html_content: str) -> str:
        """
        Parse raw HTML content and extract standard body paragraphs.
        """
        if not html_content:
            return "Failed to fetch article body."
            
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Find main article layout
            article_body = soup.find("article") or soup.find(class_=re.compile(r"article-content|entry-content|post-content|body"))
            target = article_body if article_body else soup
            
            paragraphs = target.find_all("p")
            text_blocks = []
            for p in paragraphs:
                p_text = p.get_text().strip()
                if len(p_text.split()) > 8 and not any(x in p_text.lower() for x in ["cookie", "privacy policy", "all rights reserved", "subscribe to"]):
                    text_blocks.append(p_text)
                    
            full_text = "\n\n".join(text_blocks)
            if not full_text:
                full_text = soup.get_text()
                
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            if len(full_text) > 8000:
                full_text = full_text[:8000] + " ... [truncated]"
            return full_text
        except Exception as e:
            Logger.warn(f"HTML parsing exception: {e}")
            return "Exception parsing article content."

    def crawl(self) -> List[NewsEntity]:
        """
        Fetch news from all 5 RSS feeds, filter for freshness constraints,
        and download page contents concurrently using asyncio.
        """
        Logger.info("Starting AI News RSS Feed Crawler...")
        now_utc = datetime.now(timezone.utc)
        cutoff_24h = now_utc - timedelta(hours=24)
        
        fresh_metadata = []

        for source_name, feed_url in self.sources.items():
            Logger.info(f"Checking feed: {source_name}...")
            try:
                r = requests.get(feed_url, headers=self.headers, timeout=12)
                if r.status_code != 200:
                    Logger.warn(f"Failed to fetch feed {source_name}. Code: {r.status_code}")
                    continue
                
                root = ET.fromstring(r.content)
                channel = root.find("channel")
                
                items = []
                if channel is not None:
                    items = channel.findall("item")
                    for item in items:
                        title_el = item.find("title")
                        link_el = item.find("link")
                        date_el = item.find("pubDate")
                        
                        if title_el is not None and link_el is not None:
                            title = title_el.text.strip()
                            link = link_el.text.strip()
                            pub_date_str = date_el.text.strip() if date_el is not None else ""
                            
                            pub_dt = self.parse_rss_date(pub_date_str)
                            
                            # Heuristic freshness check:
                            # 1. If date is available, must be within the last 24 hours.
                            # 2. If date is missing/unparseable, check if URL is unseen.
                            is_fresh = False
                            if pub_dt:
                                is_fresh = pub_dt >= cutoff_24h
                            else:
                                is_fresh = not self.cache.is_seen(link)
                                if is_fresh:
                                    Logger.info(f"   [HEURISTIC FRESH] No strict date, but URL is new: {title}")
                                    
                            if is_fresh and not self.cache.is_seen(link):
                                fresh_metadata.append({
                                    "source_name": source_name,
                                    "source_url": link,
                                    "title": title,
                                    "published_date": (pub_dt or now_utc).isoformat() + "Z"
                                })
                else:
                    # Atom feed parsing
                    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
                    for entry in entries:
                        title_el = entry.find("{http://www.w3.org/2005/Atom}title")
                        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                        date_el = entry.find("{http://www.w3.org/2005/Atom}published") or entry.find("{http://www.w3.org/2005/Atom}updated")
                        
                        if title_el is not None and link_el is not None:
                            title = title_el.text.strip()
                            link = link_el.attrib.get("href", "").strip()
                            pub_date_str = date_el.text.strip() if date_el is not None else ""
                            
                            pub_dt = self.parse_rss_date(pub_date_str)
                            
                            is_fresh = False
                            if pub_dt:
                                is_fresh = pub_dt >= cutoff_24h
                            else:
                                is_fresh = not self.cache.is_seen(link)
                                if is_fresh:
                                    Logger.info(f"   [HEURISTIC FRESH] No strict date, but URL is new: {title}")
                                    
                            if is_fresh and not self.cache.is_seen(link):
                                fresh_metadata.append({
                                    "source_name": source_name,
                                    "source_url": link,
                                    "title": title,
                                    "published_date": (pub_dt or now_utc).isoformat() + "Z"
                                })
                                
            except Exception as e:
                Logger.error(f"Error crawling feed {source_name}: {e}")

        # Remove duplicate links within the same run
        unique_fresh = {}
        for m in fresh_metadata:
            url = m["source_url"]
            if url not in unique_fresh:
                unique_fresh[url] = m
                
        fresh_list = list(unique_fresh.values())
        if not fresh_list:
            Logger.info("No fresh news articles found in the last 24 hours.")
            return []

        Logger.info(f"Found {len(fresh_list)} fresh article links. Crawling text contents asynchronously...")
        urls = [m["source_url"] for m in fresh_list]
        
        # Async fetch HTML
        loop = asyncio.get_event_loop()
        html_contents = loop.run_until_complete(fetch_all_urls_async(urls, self.headers))
        
        fresh_articles = []
        for i, meta in enumerate(fresh_list):
            html = html_contents[i]
            full_text = self.clean_html_to_paragraphs(html)
            
            # Register in cache
            self.cache.add(meta["source_url"])
            
            entity = NewsEntity(
                source_name=meta["source_name"],
                source_url=meta["source_url"],
                title=meta["title"],
                published_date=meta["published_date"],
                full_text=full_text
            )
            fresh_articles.append(entity)
            Logger.info(f"   [PROCESSED ASYNC] {meta['source_name']} - {meta['title']}")

        Logger.success(f"Ingested {len(fresh_articles)} fresh news articles.")
        return fresh_articles
