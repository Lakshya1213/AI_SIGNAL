from dataclasses import dataclass
from datetime import datetime

@dataclass
class JobEntity:
    company: str
    date: str
    is_remote: bool
    role_family: str
    schema_version: str = "1.0"
    record_type: str = "JOB"
    collected_at: str = None

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "schemaVersion": self.schema_version,
            "recordType": self.record_type,
            "content": {
                "company": self.company,
                "date": self.date,
                "is_remote": self.is_remote,
                "role_family": self.role_family
            },
            "collectedAt": self.collected_at
        }
