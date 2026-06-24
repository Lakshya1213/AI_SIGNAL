from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"

@dataclass
class ProductEntity:
    source_name: str
    source_url: str
    startup_name: str
    pricing_model: PricingModel
    product_name: str = None
    schema_version: str = "1.0"
    record_type: str = "PRODUCT"
    collected_at: str = None

    def __post_init__(self):
        if not self.collected_at:
            self.collected_at = datetime.utcnow().isoformat() + "Z"
        # Validate pricing model
        if isinstance(self.pricing_model, str):
            try:
                self.pricing_model = PricingModel(self.pricing_model.upper())
            except ValueError:
                self.pricing_model = PricingModel.FREEMIUM  # fallback default

    def to_dict(self) -> dict:
        content = {
            "startupName": self.startup_name,
            "pricingModel": self.pricing_model.value
        }
        if self.product_name:
            content["productName"] = self.product_name
            
        return {
            "schemaVersion": self.schema_version,
            "recordType": self.record_type,
            "source": {
                "name": self.source_name,
                "url": self.source_url
            },
            "content": content,
            "collectedAt": self.collected_at
        }
