"""Logging: every step writes what it did to the screen AND to logs/pipeline.log."""
import logging

from pipelines.config import LOG_DIR


def get_logger(name: str = "pipeline") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # already set up, don't add handlers twice
        return logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
