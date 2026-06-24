import os
from openai import OpenAI
from src.llm.retry_handler import with_retry
from src.utils.logger import Logger

class DeepSeekProvider:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.client = None
        self.model_name = "deepseek-chat"
        
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com/v1"
                )
                Logger.info("DeepSeek provider initialized successfully.")
            except Exception as e:
                Logger.error(f"Failed to initialize DeepSeek client: {e}")
        else:
            Logger.warn("DEEPSEEK_API_KEY not found. DeepSeek provider is disabled.")

    def is_available(self) -> bool:
        return self.client is not None

    @with_retry(max_retries=3, base_delay=2.0, exceptions_to_catch=(Exception,))
    def generate(self, prompt: str) -> str:
        if not self.is_available():
            raise ValueError("DeepSeek API key is missing or client not initialized.")
        
        Logger.info("Invoking DeepSeek chat model...")
        completion = self.client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model=self.model_name,
            temperature=0.1
        )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Empty response received from DeepSeek.")
        return content
