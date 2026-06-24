import os
from groq import Groq
from src.llm.retry_handler import with_retry
from src.utils.logger import Logger

class GroqProvider:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.client = None
        self.model_name = "llama-3.1-8b-instant"
        
        if self.api_key:
            try:
                self.client = Groq(api_key=self.api_key)
                Logger.info("Groq provider initialized successfully.")
            except Exception as e:
                Logger.error(f"Failed to initialize Groq client: {e}")
        else:
            Logger.warn("GROQ_API_KEY not found. Groq provider is disabled.")

    def is_available(self) -> bool:
        return self.client is not None

    @with_retry(max_retries=3, base_delay=2.0, exceptions_to_catch=(Exception,))
    def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise ValueError("Groq API key is missing or client not initialized.")
        
        Logger.info(f"Invoking Groq Llama 3 ({self.model_name})...")
        completion = self.client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=self.model_name,
            temperature=0.1
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Empty response received from Groq.")
        return content
