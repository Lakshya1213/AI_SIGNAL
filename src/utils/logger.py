import sys
from datetime import datetime

class Logger:
    @staticmethod
    def _log(level: str, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {msg}"
        print(formatted, flush=True)

    @staticmethod
    def info(msg: str):
        Logger._log("INFO", msg)

    @staticmethod
    def success(msg: str):
        Logger._log("SUCCESS", msg)

    @staticmethod
    def warn(msg: str):
        Logger._log("WARN", msg)

    @staticmethod
    def error(msg: str):
        Logger._log("ERROR", msg)

    @staticmethod
    def debug(msg: str):
        Logger._log("DEBUG", msg)
