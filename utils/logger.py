"""
utils/logger.py
Configures logging to both console and file.
"""

import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from config.settings import LOG_FILE


def cleanup_old_logs(log_dir: str, days: int = 3):
    """
    Manually deletes any files in the log directory older than the specified days.
    """
    if not os.path.exists(log_dir):
        return

    now = time.time()
    cutoff = now - (days * 86400)

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if os.path.isfile(filepath):
            # Skip hidden files or current log if needed, but here we check mtime
            if os.path.getmtime(filepath) < cutoff:
                try:
                    os.remove(filepath)
                except Exception:
                    # File might be locked by another process
                    pass


def setup_logger(name: str = "recruiter_bot") -> logging.Logger:
    """
    Returns a logger that writes to both console and logs/app.log.
    Rotates daily and keeps only 3 days of logs.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG and above)
    log_dir = os.path.dirname(LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)

    # Run manual cleanup for any orphaned logs
    cleanup_old_logs(log_dir, days=3)

    # TimedRotatingFileHandler: Rotates every day ('D'), keeps 3 backups
    file_handler = TimedRotatingFileHandler(
        LOG_FILE, when="D", interval=1, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
