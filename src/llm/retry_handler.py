import time
import random
from typing import Callable, Any
from src.utils.logger import Logger

def with_retry(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions_to_catch: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying API calls with exponential backoff and jitter.
    Copes with rate limits (429) and transient network drops.
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            delay = base_delay
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as e:
                    retries += 1
                    err_msg = str(e)
                    
                    # Log rate limit specific messages
                    is_rate_limit = "429" in err_msg or "rate limit" in err_msg.lower() or "resourceexhausted" in err_msg.lower()
                    
                    if retries > max_retries:
                        Logger.error(f"Failed after {max_retries} retries. Error: {err_msg}")
                        raise e
                    
                    # Jitter is random variation in the delay to prevent thundering herd problem
                    jitter = random.uniform(0.1, 0.5) * delay
                    sleep_time = delay + jitter
                    sleep_time = min(sleep_time, max_delay)
                    
                    if is_rate_limit:
                        Logger.warn(f"Rate limit (429) hit calling {func.__name__}. Retry {retries}/{max_retries} in {sleep_time:.2f}s...")
                    else:
                        Logger.warn(f"Transient error calling {func.__name__}: {err_msg}. Retry {retries}/{max_retries} in {sleep_time:.2f}s...")
                    
                    time.sleep(sleep_time)
                    delay *= 2  # Exponential backoff
        return wrapper
    return decorator
