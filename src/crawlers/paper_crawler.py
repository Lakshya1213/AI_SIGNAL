import requests
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import sys
import os
# Add project root to sys.path to allow running/importing directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.schemas.paper_schema import PaperEntity
from src.utils.logger import Logger

class PaperCrawler:
    def __init__(self, use_mock: bool = False):
        self.api_url = "https://huggingface.co/api/daily_papers"
        self.use_mock = use_mock
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_papers_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Fetch daily papers for a specific date from Hugging Face.
        """
        try:
            r = requests.get(self.api_url, params={"date": date_str}, headers=self.headers, timeout=10)
            if r.status_code == 200:
                return r.json()
            else:
                Logger.warn(f"Failed to fetch papers for {date_str}. Code: {r.status_code}")
                return []
        except Exception as e:
            Logger.warn(f"Error fetching papers for {date_str}: {e}")
            return []

    def get_github_stars(self, url: str) -> int:
        """
        Scrape current GitHub star count for a repository.
        """
        if not url:
            return 0
            
        if self.use_mock:
            # Deterministic mock star count based on length of URL
            return (len(url) * 7) % 500 + 12
            
        if "github.com" not in url.lower():
            return 0
            
        # Clean URL to get the base repository path: https://github.com/owner/repo
        # Match github.com/owner/repo structure
        match = re.search(r'github\.com/([^/]+)/([^/#\?\s]+)', url)
        if not match:
            return 0
            
        owner = match.group(1)
        repo = match.group(2)
        # Suffix clean (e.g. remove .git if present)
        if repo.endswith(".git"):
            repo = repo[:-4]
            
        repo_url = f"https://github.com/{owner}/{repo}"
        
        try:
            r = requests.get(repo_url, headers=self.headers, timeout=8)
            if r.status_code == 200:
                html = r.text
                star_match = re.search(r'id="repo-stars-counter-star"[^>]*>([\d\.,\sKkMmbB]+)</span>', html)
                if star_match:
                    val = star_match.group(1).strip().replace(",", "")
                    if "k" in val.lower():
                        val = float(val.lower().replace("k", "")) * 1000
                    elif "m" in val.lower():
                        val = float(val.lower().replace("m", "")) * 1000000
                    return int(val)
            else:
                Logger.warn(f"GitHub page for {repo_url} returned code {r.status_code}")
        except Exception as e:
            Logger.warn(f"Failed to scrape GitHub stars for {repo_url}: {e}")
            
        return 0

    def crawl(self, limit: int = 1000) -> List[PaperEntity]:
        """
        Collect N papers with associated GitHub repos and resolve their stars.
        """
        Logger.info(f"Starting paper crawler to collect {limit} papers...")
        unique_papers = {}
        base_date = datetime.now()
        days_scanned = 0
        
        # Phase 1: Collect metadata from daily papers API going backward
        while len(unique_papers) < limit and days_scanned < 180:  # max scan 6 months
            date_str = (base_date - timedelta(days=days_scanned)).strftime("%Y-%m-%d")
            days_scanned += 1
            
            raw_papers = self.fetch_papers_for_date(date_str)
            if not raw_papers:
                continue
                
            new_found = 0
            for item in raw_papers:
                paper_data = item.get("paper", {})
                arxiv_id = paper_data.get("id")
                github_repo = paper_data.get("githubRepo")
                
                if arxiv_id and github_repo and arxiv_id not in unique_papers:
                    # Parse authors
                    authors = [a.get("name") for a in paper_data.get("authors", []) if a.get("name")]
                    
                    # Publication date
                    pub_date = paper_data.get("publishedAt") or item.get("publishedAt")
                    
                    # Ensure full github URL
                    github_url = github_repo.strip()
                    if "github.com" not in github_url.lower() and "/" in github_url:
                        github_url = f"https://github.com/{github_url.lstrip('/')}"
                    
                    unique_papers[arxiv_id] = {
                        "title": paper_data.get("title", ""),
                        "authors": authors,
                        "paper_url": f"https://arxiv.org/abs/{arxiv_id}",
                        "github_url": github_url,
                        "published_date": pub_date
                    }
                    new_found += 1
                    
                    if len(unique_papers) >= limit:
                        break
                        
            if new_found > 0:
                Logger.info(f"Date {date_str}: Found {new_found} new papers with code. Total: {len(unique_papers)}/{limit}")
                
        # Phase 2: Fetch github star counts concurrently
        paper_list = list(unique_papers.values())
        Logger.info(f"Collected {len(paper_list)} paper metadata. Now fetching GitHub stars in parallel...")
        
        # Concurrently fetch stars using ThreadPoolExecutor
        max_workers = 10
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a mapping of future to paper dict
            future_to_paper = {
                executor.submit(self.get_github_stars, paper["github_url"]): paper
                for paper in paper_list
            }
            
            completed = 0
            for future in as_completed(future_to_paper):
                paper = future_to_paper[future]
                try:
                    stars = future.result()
                    paper["github_stars"] = stars
                except Exception as e:
                    Logger.warn(f"Error resolving stars for {paper['github_url']}: {e}")
                    paper["github_stars"] = 0
                    
                completed += 1
                if completed % 50 == 0 or completed == len(paper_list):
                    Logger.info(f"GitHub stars resolution: {completed}/{len(paper_list)} completed.")
                
                # Tiny sleep to reduce aggressive hit rate on github
                if not self.use_mock:
                    time.sleep(0.05)
 
        # Convert to PaperEntities
        entities = []
        for p in paper_list:
            entities.append(PaperEntity(
                title=p["title"],
                authors=p["authors"],
                paper_url=p["paper_url"],
                github_url=p["github_url"],
                github_stars=p["github_stars"],
                published_date=p["published_date"]
            ))
            
        Logger.success(f"Successfully processed {len(entities)} canonical Research Paper records.")
        return entities
