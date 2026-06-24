from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class StartupEntity:
    source_name: str
    source_url: str
    entity_name: str
    employee_count: int = None
    schema_version: str = "1.0"
    record_type: str = "STARTUP"
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
                "entityName": self.entity_name,
                "data": {
                    "employeeCount": self.employee_count
                }
            },
            "collectedAt": self.collected_at
        }
