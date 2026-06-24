import re
from bs4 import BeautifulSoup
from src.utils.logger import Logger

def clean_html(html_content: str) -> str:
    """
    Remove HTML tags, scripts, styles and normalize whitespaces.
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link", "noscript", "iframe"]):
            script.decompose()
            
        # Get text
        text = soup.get_text(separator=" ")
        
        # Normalize whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Clean extra newlines/spaces
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    except Exception as e:
        Logger.warn(f"HTML cleaning failed: {e}. Returning raw text.")
        # Fallback to simple regex clean if bs4 fails
        text = re.sub(r'<[^>]*>', ' ', html_content)
        return re.sub(r'\s+', ' ', text).strip()

def truncate_payload(text: str, max_chars: int = 12000) -> str:
    """
    Truncate text to a maximum character length while preserving word/sentence boundaries.
    """
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
        
    Logger.info(f"Payload too large ({len(text)} chars). Truncating to {max_chars} chars.")
    # Truncate at word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space != -1 and last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
        
    return truncated + "\n... [truncated due to length] ..."
