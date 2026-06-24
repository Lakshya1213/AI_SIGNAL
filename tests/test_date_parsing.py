import sys
import os
# Add project root to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.job_crawler import JobCrawler
from src.entity_resolution.resolver import EntityResolver

def test_rss_date_parsing():
    crawler = NewsCrawler()
    
    # Test RFC 822 format with offset
    dt1 = crawler.parse_rss_date("Sun, 21 Jun 2026 15:28:17 +0000")
    assert dt1 is not None
    assert dt1.year == 2026
    assert dt1.month == 6
    assert dt1.day == 21
    assert dt1.hour == 15
    assert dt1.minute == 28
    
    # Test RFC 822 format with named TZ
    dt2 = crawler.parse_rss_date("Tue, 19 May 2026 17:45:00 GMT")
    assert dt2 is not None
    assert dt2.year == 2026
    assert dt2.month == 5
    assert dt2.day == 19
    assert dt2.hour == 17
    assert dt2.tzinfo == timezone.utc

def test_job_date_parsing():
    resolver = EntityResolver()
    crawler = JobCrawler(resolver=resolver)
    
    # Test ISO 8601 format
    dt = crawler.parse_job_date("2026-06-22T14:35:10Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 6
    assert dt.day == 22
    assert dt.hour == 14
    assert dt.minute == 35
    assert dt.tzinfo == timezone.utc
