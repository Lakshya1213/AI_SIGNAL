import sys
import os
# Add project root to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.entity_resolution.resolver import EntityResolver

def test_entity_resolver_seed_matching():
    resolver = EntityResolver()
    
    # Exact match on seed list
    assert resolver.resolve_startup("OpenAI") == "OpenAI"
    
    # Messy suffix match
    assert resolver.resolve_startup("OpenAI, Inc.") == "OpenAI"
    assert resolver.resolve_startup("Anthropic Corp") == "Anthropic"
    
    # Fuzzy match with spaces
    assert resolver.resolve_startup("Open AI") == "OpenAI"
    assert resolver.resolve_startup("ScaleAI") == "Scale AI"

def test_entity_resolver_non_seed():
    resolver = EntityResolver()
    
    # Non-seed company should be cleaned but not mapped to seed
    assert resolver.resolve_startup("CircuitHub, Inc.") == "CircuitHub"
    
    # Mapping log structure verification
    log = resolver.get_mapping_log()
    assert len(log) > 0
    assert "raw_name" in log[0]
    assert "canonical_name" in log[0]
    assert "similarity_score" in log[0]
    assert "matched_seed" in log[0]
