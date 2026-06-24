import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import re
from typing import List, Dict, Any, Optional
import sys
import os

# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.schemas.job_schema import JobEntity
from src.entity_resolution.resolver import EntityResolver
from src.utils.seen_cache import SeenCache
from src.utils.logger import Logger

from src.llm.llm_orchestrator import LLMOrchestrator

class JobCrawler:
    def __init__(self, resolver: EntityResolver, orchestrator: LLMOrchestrator = None, cache: SeenCache = None):
        self.resolver = resolver
        self.orchestrator = orchestrator or LLMOrchestrator(use_mock=True)
        self.cache = cache or SeenCache()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def classify_role_family(self, title: str) -> str:
        """
        Classify job title into standard functional categories.
        """
        title_lower = title.lower()
        if any(x in title_lower for x in ["researcher", "research scientist", "postdoc", "scientist", "ai scientist"]):
            return "Research"
        elif any(x in title_lower for x in ["engineer", "developer", "architect", "programmer", "technical", "coding", "software", "infrastructure", "devops", "platform", "backend", "frontend", "fullstack", "full-stack", "compiler", "mlops"]):
            return "Engineering"
        elif any(x in title_lower for x in ["product manager", "pm", "product lead", "product director"]):
            return "Product"
        elif any(x in title_lower for x in ["designer", "ux", "ui", "creative", "art", "graphic"]):
            return "Design"
        elif any(x in title_lower for x in ["sales", "account executive", "ae", "business development", "bizdev", "sales manager"]):
            return "Sales"
        elif any(x in title_lower for x in ["marketing", "growth", "seo", "content writer", "communications", "pr"]):
            return "Marketing"
        elif any(x in title_lower for x in ["hr", "recruiter", "talent", "human resources", "people partner"]):
            return "HR"
        elif any(x in title_lower for x in ["finance", "accountant", "controller", "treasury"]):
            return "Finance"
        elif any(x in title_lower for x in ["legal", "compliance", "counsel"]):
            return "Legal"
        else:
            return "Operations"

    def parse_job_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse job publication dates from RSS feeds and APIs into UTC datetime.
        """
        if not date_str:
            return None
        date_str = date_str.strip()
        
        formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d"
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

    def check_is_remote(self, title: str, location_name: str) -> bool:
        """
        Determine remote eligibility based on title and location name.
        """
        search_str = f"{title} {location_name}".lower()
        return any(x in search_str for x in ["remote", "telecommute", "anywhere", "work from home", "wfh"])

    def crawl_greenhouse(self, company_id: str, company_name: str, cutoff: datetime) -> List[JobEntity]:
        """
        Crawl a Greenhouse job board API.
        """
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
        Logger.info(f"Crawling Greenhouse board for {company_name}...")
        jobs = []
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                raw_jobs = data.get("jobs", [])
                for rj in raw_jobs:
                    job_url = rj.get("absolute_url")
                    updated_at_str = rj.get("updated_at")
                    
                    dt = self.parse_job_date(updated_at_str)
                    
                    is_fresh = False
                    if dt:
                        is_fresh = dt >= cutoff
                    else:
                        is_fresh = not self.cache.is_seen(job_url)
                        if is_fresh:
                            Logger.info(f"   [HEURISTIC FRESH] No date, but unseen job posting: {rj.get('title')}")
                            
                    if is_fresh and not self.cache.is_seen(job_url):
                        title = rj.get("title", "")
                        loc = rj.get("location", {}).get("name", "")
                        
                        # Use LLM fallback chain to extract job details
                        extracted = self.orchestrator.extract_job_details(
                            title=title,
                            description=rj.get("content", "") or title,
                            location=loc
                        )
                        
                        canonical_company = self.resolver.resolve_startup(extracted.get("company") if extracted.get("company") != "Unknown" else company_name)
                        is_remote = extracted.get("is_remote", False)
                        role_fam = extracted.get("role_family", "Engineering")
                        self.cache.add(job_url)
                        
                        entity = JobEntity(
                            company=canonical_company,
                            date=(dt or datetime.now(timezone.utc)).isoformat() + "Z",
                            is_remote=is_remote,
                            role_family=role_fam
                        )
                        jobs.append(entity)
                        Logger.info(f"   [FRESH JOB] {company_name} - {title}")
            else:
                Logger.warn(f"Failed to fetch Greenhouse board for {company_name}. Code: {r.status_code}")
        except Exception as e:
            Logger.error(f"Error crawling Greenhouse board for {company_name}: {e}")
        return jobs

    def crawl_remotive(self, cutoff: datetime) -> List[JobEntity]:
        """
        Crawl Remotive Job API.
        """
        url = "https://remotive.com/api/remote-jobs"
        Logger.info("Crawling Remotive API...")
        jobs = []
        try:
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                raw_jobs = data.get("jobs", [])
                for rj in raw_jobs:
                    job_url = rj.get("url")
                    pub_date_str = rj.get("publication_date")
                    
                    dt = self.parse_job_date(pub_date_str)
                    
                    is_fresh = False
                    if dt:
                        is_fresh = dt >= cutoff
                    else:
                        is_fresh = not self.cache.is_seen(job_url)
                        if is_fresh:
                            Logger.info(f"   [HEURISTIC FRESH] No date, but unseen job: {rj.get('title')}")
                            
                    if is_fresh and not self.cache.is_seen(job_url):
                        title = rj.get("title", "")
                        title_lower = title.lower()
                        is_ai = any(x in title_lower for x in ["ai", "ml", "machine learning", "deep learning", "nlp", "llm", "data scientist", "computer vision", "artificial intelligence"])
                        
                        if is_ai:
                            company = rj.get("company_name", "")
                            
                            # Use LLM fallback chain to extract job details
                            extracted = self.orchestrator.extract_job_details(
                                title=title,
                                description=rj.get("description", "") or title,
                                location="Remote"
                            )
                            
                            canonical_company = self.resolver.resolve_startup(extracted.get("company") if extracted.get("company") != "Unknown" else company)
                            role_fam = extracted.get("role_family", "Engineering")
                            is_remote = extracted.get("is_remote", True)
                            self.cache.add(job_url)
                            
                            entity = JobEntity(
                                company=canonical_company,
                                date=(dt or datetime.now(timezone.utc)).isoformat() + "Z",
                                is_remote=is_remote,
                                role_family=role_fam
                            )
                            jobs.append(entity)
                            Logger.info(f"   [FRESH JOB] Remotive - {company} - {title}")
            else:
                Logger.warn(f"Failed to fetch Remotive jobs. Code: {r.status_code}")
        except Exception as e:
            Logger.error(f"Error crawling Remotive jobs: {e}")
        return jobs

    def crawl_aijobs_net(self, cutoff: datetime) -> List[JobEntity]:
        """
        Crawl ai-jobs.net RSS feed.
        """
        url = "https://ai-jobs.net/feed/"
        Logger.info("Crawling ai-jobs.net RSS feed...")
        jobs = []
        try:
            r = requests.get(url, headers=self.headers, timeout=12)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                channel = root.find("channel")
                if channel is not None:
                    items = channel.findall("item")
                    for item in items:
                        job_url = item.find("link").text if item.find("link") is not None else ""
                        pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        
                        dt = self.parse_job_date(pub_date_str)
                        
                        is_fresh = False
                        if dt:
                            is_fresh = dt >= cutoff
                        else:
                            is_fresh = not self.cache.is_seen(job_url)
                            if is_fresh:
                                Logger.info(f"   [HEURISTIC FRESH] No date, but unseen job: {item.find('title').text}")
                                
                        if is_fresh and not self.cache.is_seen(job_url):
                            raw_title = item.find("title").text if item.find("title") is not None else ""
                            title = raw_title
                            company = "Unknown"
                            
                            match = re.search(r'^(.*?)\s+at\s+(.*?)(?:\s+\(.*?\))?$', raw_title)
                            if match:
                                title = match.group(1).strip()
                                company = match.group(2).strip()
                                if " (" in company:
                                    company = company.split(" (")[0].strip()
                            
                            desc = item.find("description").text if item.find("description") is not None else ""
                            
                            # Use LLM fallback chain to extract job details
                            extracted = self.orchestrator.extract_job_details(
                                title=title,
                                description=desc or title,
                                location="Remote"
                            )
                            
                            canonical_company = self.resolver.resolve_startup(extracted.get("company") if extracted.get("company") != "Unknown" else company)
                            role_fam = extracted.get("role_family", "Engineering")
                            is_remote = extracted.get("is_remote", False)
                            self.cache.add(job_url)
                            
                            entity = JobEntity(
                                company=canonical_company,
                                date=(dt or datetime.now(timezone.utc)).isoformat() + "Z",
                                is_remote=is_remote,
                                role_family=role_fam
                            )
                            jobs.append(entity)
                            Logger.info(f"   [FRESH JOB] ai-jobs.net - {company} - {title}")
            else:
                Logger.warn(f"Failed to fetch ai-jobs.net RSS. Code: {r.status_code}")
        except Exception as e:
            Logger.error(f"Error crawling ai-jobs.net RSS: {e}")
        return jobs

    def crawl(self) -> List[JobEntity]:
        """
        Aggregate fresh jobs from all 5 boards.
        """
        Logger.info("Starting AI Jobs Ingestion...")
        fresh_jobs = []
        now_utc = datetime.now(timezone.utc)
        cutoff_24h = now_utc - timedelta(hours=24)

        # Greenhouse APIs
        fresh_jobs.extend(self.crawl_greenhouse("scaleai", "Scale AI", cutoff_24h))
        fresh_jobs.extend(self.crawl_greenhouse("assemblyai", "AssemblyAI", cutoff_24h))
        fresh_jobs.extend(self.crawl_greenhouse("togetherai", "Together AI", cutoff_24h))

        # Remotive
        fresh_jobs.extend(self.crawl_remotive(cutoff_24h))

        # ai-jobs.net
        fresh_jobs.extend(self.crawl_aijobs_net(cutoff_24h))

        Logger.success(f"Ingested {len(fresh_jobs)} fresh jobs.")
        return fresh_jobs
