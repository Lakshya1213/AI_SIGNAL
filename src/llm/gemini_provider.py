import os
import warnings
# Suppress FutureWarnings from polluting console logs
warnings.filterwarnings("ignore", category=FutureWarning)

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError
from src.llm.retry_handler import with_retry
from src.utils.logger import Logger

class GeminiProvider:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Using gemini-2.5-flash as the default fast and robust model
                self.model = genai.GenerativeModel("gemini-2.5-flash")
                Logger.info("Gemini provider initialized successfully.")
            except Exception as e:
                Logger.error(f"Failed to configure Gemini SDK: {e}")
        else:
            Logger.warn("GEMINI_API_KEY not found. Gemini provider is disabled.")

    def is_available(self) -> bool:
        return self.model is not None

    @with_retry(max_retries=3, base_delay=2.0, exceptions_to_catch=(GoogleAPICallError, Exception))
    def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise ValueError("Gemini API key is missing or model not initialized.")
        
        Logger.info("Invoking Gemini Flash model...")
        response = self.model.generate_content(prompt)
        if not response or not response.text:
            raise ValueError("Empty response received from Gemini.")
        return response.text
