import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", logger_name: Optional[str] = None) -> logging.Logger:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    if logger_name:
        return logging.getLogger(logger_name)
    return logging.getLogger()

