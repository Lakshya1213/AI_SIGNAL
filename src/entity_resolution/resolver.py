import re
from typing import Tuple, Dict, Any, List
from rapidfuzz import fuzz, process
from src.entity_resolution.canonical_db import SEED_STARTUPS
from src.utils.logger import Logger

class EntityResolver:
    def __init__(self, threshold: float = 82.0):
        self.seed_list = SEED_STARTUPS
        self.threshold = threshold
        self.mapping_log: List[Dict[str, Any]] = []

    def clean_name(self, name: str) -> str:
        """
        Clean common business suffixes and normalize formatting.
        """
        if not name:
            return ""
        # Remove common business endings
        name_clean = re.sub(r'\b(inc|corp|co|ltd|gmbh|sa|pvt|public|limited|corporation|incorporated)\b\.?', '', name, flags=re.IGNORECASE)
        # Remove punctuation except spaces
        name_clean = re.sub(r'[^\w\s-]', '', name_clean)
        # Normalize whitespace
        name_clean = re.sub(r'\s+', ' ', name_clean).strip()
        return name_clean

    def resolve_startup(self, raw_name: str) -> str:
        """
        Resolve a raw startup name to a canonical name, mapping it to the seed list if it matches.
        """
        if not raw_name:
            return ""
            
        cleaned_raw = self.clean_name(raw_name)
        if not cleaned_raw:
            return raw_name
            
        # Try direct matches after cleaning (ignoring case and spaces)
        cleaned_raw_nospace = cleaned_raw.replace(" ", "").lower()
        for seed in self.seed_list:
            seed_clean = self.clean_name(seed)
            if cleaned_raw_nospace == seed.replace(" ", "").lower() or cleaned_raw_nospace == seed_clean.replace(" ", "").lower():
                self._log_mapping(raw_name, seed, 100.0, True)
                return seed
                
        # Perform fuzzy matching on seed list
        # We search matching against raw seed names and cleaned seed names
        best_match = None
        best_score = 0.0
        
        for seed in self.seed_list:
            # Token sort ratio is robust to word rearrangements (e.g. "Together AI" vs "AI Together")
            score1 = fuzz.token_sort_ratio(cleaned_raw, seed)
            score2 = fuzz.token_sort_ratio(cleaned_raw, self.clean_name(seed))
            score = max(score1, score2)
            
            if score > best_score:
                best_score = score
                best_match = seed
                
        if best_score >= self.threshold and best_match:
            # Map to the matched seed company
            canonical_name = best_match
            matched_seed = True
            Logger.info(f"Resolved raw name '{raw_name}' to seed startup '{canonical_name}' (score: {best_score:.1f})")
        else:
            # Use the cleaned name as the canonical form
            canonical_name = cleaned_raw
            matched_seed = False
            
        self._log_mapping(raw_name, canonical_name, best_score, matched_seed)
        return canonical_name

    def _log_mapping(self, raw_name: str, canonical_name: str, score: float, matched_seed: bool):
        """
        Log the resolution mapping for the output sheet.
        """
        self.mapping_log.append({
            "raw_name": raw_name,
            "canonical_name": canonical_name,
            "similarity_score": round(score, 2),
            "matched_seed": "YES" if matched_seed else "NO"
        })

    def get_mapping_log(self) -> List[Dict[str, Any]]:
        return self.mapping_log
