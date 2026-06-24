import os
import json
import re
from typing import Optional, Dict, Any
from src.llm.gemini_provider import GeminiProvider
from src.llm.groq_provider import GroqProvider
from src.llm.deepseek_provider import DeepSeekProvider
from src.utils.logger import Logger

class LLMOrchestrator:
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        
        # Initialize providers
        self.gemini = GeminiProvider()
        self.groq = GroqProvider()
        self.deepseek = DeepSeekProvider()
        
        self.chain = []
        if not self.use_mock:
            if self.gemini.is_available():
                self.chain.append(self.gemini)
            if self.groq.is_available():
                self.chain.append(self.groq)
            if self.deepseek.is_available():
                self.chain.append(self.deepseek)
                
        if not self.chain and not self.use_mock:
            Logger.warn("No active LLM providers configured. Falling back to Mock parser mode.")
            self.use_mock = True

    def extract_startup_product(self, name: str, description: str, website: str, tags: list) -> Dict[str, Any]:
        """
        Extract canonical startup name, product name, pricing model, and employee count.
        """
        if self.use_mock:
            return self._mock_extraction(name, description, website, tags)
            
        prompt = f"""
You are a venture capital data analyst. Given the following startup description:
Name: {name}
Description: {description}
Website: {website}
Tags: {', '.join(tags) if tags else 'None'}

Extract the following fields in JSON format:
{{
  "canonical_startup_name": "Normalized name of the startup (remove Inc., Corp., Co., etc.)",
  "primary_product_name": "Name of their primary software or service product (defaults to startup name if unknown)",
  "pricing_model": "One of: 'FREE', 'FREEMIUM', 'PAID', 'ENTERPRISE'",
  "employee_count": null
}}

Pricing Model Guidelines:
- 'FREE': Open source or completely free with no paid options.
- 'FREEMIUM': Free tier/version available, but you pay to upgrade for more features.
- 'PAID': Subscription or usage-based payment required, self-service signup.
- 'ENTERPRISE': Targets enterprise customers, requires talking to sales/booking a demo, custom pricing.

Return ONLY a valid JSON object. Do not include markdown code block formatting (e.g. do NOT wrap in ```json). Do not include any explanation.
"""
        
        for provider in list(self.chain):
            try:
                response_text = provider.generate(prompt)
                parsed = self._parse_json_response(response_text)
                if parsed:
                    # Validate keys
                    keys = ["canonical_startup_name", "primary_product_name", "pricing_model"]
                    if all(k in parsed for k in keys):
                        Logger.success(f"Successfully extracted data using {provider.__class__.__name__}")
                        return parsed
                Logger.warn(f"Failed to parse valid JSON from {provider.__class__.__name__}. Trying next fallback.")
            except Exception as e:
                Logger.warn(f"Error invoking {provider.__class__.__name__}: {e}. Trying next fallback.")
                # Circuit breaker: Disable failing provider dynamically for speed immediately
                Logger.error(f"Disabling {provider.__class__.__name__} for the rest of the run to maintain pipeline speed.")
                if provider in self.chain:
                    self.chain.remove(provider)
                
        # If all fail, use mock fallback
        Logger.warn("All LLM providers in fallback chain failed. Using rule-based mock fallback.")
        return self._mock_extraction(name, description, website, tags)

    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Clean and parse JSON from the LLM response text.
        """
        if not text:
            return None
        text = text.strip()
        # Remove markdown code block wrappers if the LLM ignored instructions
        text = re.sub(r"^```[a-zA-Z0-9]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
        text = text.strip()
        
        # Try to find JSON block
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
            
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            Logger.warn(f"JSON decode error for text: {text[:200]}")
            return None

    def _mock_extraction(self, name: str, description: str, website: str, tags: list) -> Dict[str, Any]:
        """
        Rule-based heuristic fallback (Mock LLM).
        """
        desc_lower = description.lower() if description else ""
        tags_lower = [t.lower() for t in tags] if tags else []
        
        # Heuristic for pricing model
        pricing = "FREEMIUM"  # default
        
        if "open source" in desc_lower or "open-source" in desc_lower or "free and open source" in desc_lower or "github.com" in desc_lower:
            pricing = "FREE"
        elif "contact sales" in desc_lower or "book a demo" in desc_lower or "enterprise grade" in desc_lower or "enterprise" in tags_lower:
            pricing = "ENTERPRISE"
        elif "subscription" in desc_lower or "pricing start" in desc_lower or "billing" in desc_lower:
            pricing = "PAID"
        elif "free tier" in desc_lower or "try for free" in desc_lower or "freemium" in desc_lower:
            pricing = "FREEMIUM"
            
        # Clean canonical name using business suffix regex
        canonical_name = re.sub(r'\b(inc|corp|co|ltd|gmbh|sa|pvt|public|limited|corporation|incorporated)\b\.?', '', name, flags=re.IGNORECASE)
        canonical_name = re.sub(r'\s+', ' ', canonical_name).strip()
        
        return {
            "canonical_startup_name": canonical_name,
            "primary_product_name": canonical_name,
            "pricing_model": pricing,
            "employee_count": None
        }

    def extract_job_details(self, title: str, description: str, location: str) -> Dict[str, Any]:
        """
        Extract canonical company name, remote eligibility, and role family from a job posting using LLM fallback chain.
        """
        if self.use_mock:
            return self._mock_job_extraction(title, description, location)
            
        prompt = f"""
You are a job market data analyst. Given the following job posting:
Title: {title}
Location: {location}
Description Snippet: {description[:1000]}

Extract the following fields in JSON format:
{{
  "company": "Canonical company name",
  "is_remote": true/false (boolean, whether the job is fully remote/wfh/anywhere),
  "role_family": "One of: 'Engineering', 'Research', 'Product', 'Design', 'Sales', 'Marketing', 'HR', 'Finance', 'Legal', 'Operations'"
}}

Return ONLY a valid JSON object. Do not include markdown code blocks.
"""
        for provider in list(self.chain):
            try:
                response_text = provider.generate(prompt)
                parsed = self._parse_json_response(response_text)
                if parsed:
                    keys = ["company", "is_remote", "role_family"]
                    if all(k in parsed for k in keys):
                        # Ensure remote is boolean
                        if isinstance(parsed["is_remote"], str):
                            parsed["is_remote"] = parsed["is_remote"].lower() == "true"
                        Logger.success(f"Successfully extracted job details using {provider.__class__.__name__}")
                        return parsed
                Logger.warn(f"Failed to parse valid JSON from {provider.__class__.__name__} for job. Trying next fallback.")
            except Exception as e:
                Logger.warn(f"Error invoking {provider.__class__.__name__} for job: {e}. Trying next fallback.")
                if provider in self.chain:
                    self.chain.remove(provider)
                    
        return self._mock_job_extraction(title, description, location)

    def _mock_job_extraction(self, title: str, description: str, location: str) -> Dict[str, Any]:
        """
        Fallback job extraction using rule-based heuristics.
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        
        # is_remote
        search_str = f"{title} {location} {desc_lower}".lower()
        is_remote = any(x in search_str for x in ["remote", "telecommute", "anywhere", "work from home", "wfh"])
        
        # role_family
        if any(x in title_lower for x in ["researcher", "research scientist", "postdoc", "scientist", "ai scientist"]):
            role_family = "Research"
        elif any(x in title_lower for x in ["engineer", "developer", "architect", "programmer", "technical", "coding", "software", "infrastructure", "devops", "platform", "backend", "frontend", "fullstack", "full-stack", "compiler", "mlops"]):
            role_family = "Engineering"
        elif any(x in title_lower for x in ["product manager", "pm", "product lead", "product director"]):
            role_family = "Product"
        elif any(x in title_lower for x in ["designer", "ux", "ui", "creative", "art", "graphic"]):
            role_family = "Design"
        elif any(x in title_lower for x in ["sales", "account executive", "ae", "business development", "bizdev", "sales manager"]):
            role_family = "Sales"
        elif any(x in title_lower for x in ["marketing", "growth", "seo", "content writer", "communications", "pr"]):
            role_family = "Marketing"
        elif any(x in title_lower for x in ["hr", "recruiter", "talent", "human resources", "people partner"]):
            role_family = "HR"
        elif any(x in title_lower for x in ["finance", "accountant", "controller", "treasury"]):
            role_family = "Finance"
        elif any(x in title_lower for x in ["legal", "compliance", "counsel"]):
            role_family = "Legal"
        else:
            role_family = "Operations"
            
        return {
            "company": "Unknown",
            "is_remote": is_remote,
            "role_family": role_family
        }
