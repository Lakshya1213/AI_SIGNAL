from dataclasses import dataclass, field
from typing import List
from datetime import datetime

@dataclass
class PaperEntity:
    title: str
    authors: List[str] = field(default_factory=list)
    paper_url: str = None
    github_url: str = None
    github_stars: int = 0
    published_date: str = None
    schema_version: str = "1.0"
    record_type: str = "RESEARCH_PAPER"
    collected_at: str = None

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "schemaVersion": self.schema_version,
            "recordType": self.record_type,
            "content": {
                "title": self.title,
                "authors": self.authors,
                "paper_url": self.paper_url,
                "github_url": self.github_url,
                "github_stars": self.github_stars,
                "published_date": self.published_date
            },
            "collectedAt": self.collected_at
        }
