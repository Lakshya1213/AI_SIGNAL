from dataclasses import dataclass
from datetime import datetime

@dataclass
class NewsEntity:
    source_name: str
    source_url: str
    title: str
    published_date: str
    full_text: str
    schema_version: str = "1.0"
    record_type: str = "NEWS"
    collected_at: str = None

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "schemaVersion": self.schema_version,
            "recordType": self.record_type,
            "source": {
                "name": self.source_name,
                "url": self.source_url
            },
            "content": {
                "title": self.title,
                "published_date": self.published_date,
                "fullText": self.full_text
            },
            "collectedAt": self.collected_at
        }
