import sys
import os
# Add project root to sys.path to allow imports from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.llm.llm_orchestrator import LLMOrchestrator

def test_mock_llm_pricing_classification():
    # Force mock mode for testing
    orchestrator = LLMOrchestrator(use_mock=True)
    
    # 1. FREE pricing heuristic (open source)
    res_free = orchestrator.extract_startup_product(
        name="LlamaIndex",
        description="LlamaIndex is an open source data framework for LLMs.",
        website="https://llamaindex.ai",
        tags=["Developer Tools", "AI"]
    )
    assert res_free["pricing_model"] == "FREE"
    assert res_free["canonical_startup_name"] == "LlamaIndex"

    # 2. ENTERPRISE pricing heuristic
    res_ent = orchestrator.extract_startup_product(
        name="Writer Corp",
        description="We build enterprise grade LLMs for secure corporate workflows. Book a demo today.",
        website="https://writer.com",
        tags=["Enterprise SaaS", "Generative AI"]
    )
    assert res_ent["pricing_model"] == "ENTERPRISE"
    assert res_ent["canonical_startup_name"] == "Writer"

    # 3. FREEMIUM pricing heuristic (try for free)
    res_free_tier = orchestrator.extract_startup_product(
        name="Cursor",
        description="An AI code editor. Try for free, upgrade to pro later.",
        website="https://cursor.com",
        tags=["Developer Tools"]
    )
    assert res_free_tier["pricing_model"] == "FREEMIUM"

def test_real_llm_fallback_chain():
    from dotenv import load_dotenv
    load_dotenv()
    
    orchestrator = LLMOrchestrator(use_mock=False)
    
    # Check if any live provider is configured; if not, skip rather than failing hard
    if len(orchestrator.chain) == 0:
        pytest.skip("No live LLM API keys configured in .env; skipping integration test.")
    
    # Run a real test extraction
    result = orchestrator.extract_startup_product(
        name="Mistral AI",
        description="We build open source and commercial frontier AI models.",
        website="https://mistral.ai",
        tags=["Generative AI", "Models"]
    )
    
    assert "canonical_startup_name" in result
    assert "pricing_model" in result
    assert result["pricing_model"] in ["FREE", "FREEMIUM", "PAID", "ENTERPRISE"]
    print(f"\n[LIVE TEST] Successful extraction: {result}")

def test_mock_llm_job_classification():
    orchestrator = LLMOrchestrator(use_mock=True)
    
    # Remote Engineering job
    res = orchestrator.extract_job_details(
        title="Senior Machine Learning Engineer",
        description="We are looking for an ML engineer. Fully remote work allowed.",
        location="Remote"
    )
    assert res["is_remote"] is True
    assert res["role_family"] == "Engineering"
    
    # Onsite Research job
    res2 = orchestrator.extract_job_details(
        title="AI Research Scientist",
        description="Join our team at the office in San Francisco.",
        location="San Francisco, CA"
    )
    assert res2["is_remote"] is False
    assert res2["role_family"] == "Research"
