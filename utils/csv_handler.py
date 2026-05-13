"""
utils/csv_handler.py
Read and write recruiter data and sent email logs to CSV files.
"""

import csv
import os
from datetime import datetime
from config.settings import RECRUITERS_CSV, SENT_LOG_CSV

RECRUITER_FIELDS = ["name", "email", "company", "keyword", "post_snippet", "extracted_at"]
SENT_LOG_FIELDS  = ["email", "sent_at", "status"]


def save_recruiters(recruiters: list[dict]) -> None:
    """
    Append recruiter records to data/recruiters.csv.
    Creates the file with headers if it doesn't exist.
    """
    os.makedirs(os.path.dirname(RECRUITERS_CSV), exist_ok=True)
    file_exists = os.path.isfile(RECRUITERS_CSV)

    with open(RECRUITERS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RECRUITER_FIELDS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()

        for r in recruiters:
            r.setdefault("extracted_at", datetime.now().isoformat(timespec="seconds"))
            writer.writerow(r)


def load_recruiters() -> list[dict]:
    """Load all recruiter records from CSV."""
    if not os.path.isfile(RECRUITERS_CSV):
        return []
    with open(RECRUITERS_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def log_sent_email(email: str, status: str = "sent") -> None:
    """
    Append an email send record to data/sent_log.csv.

    Args:
        email:  Recipient email address.
        status: 'sent', 'failed', or 'duplicate'.
    """
    os.makedirs(os.path.dirname(SENT_LOG_CSV), exist_ok=True)
    file_exists = os.path.isfile(SENT_LOG_CSV)

    with open(SENT_LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SENT_LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "email":   email,
            "sent_at": datetime.now().isoformat(timespec="seconds"),
            "status":  status,
        })


def load_sent_log() -> list[dict]:
    """Load all sent email log records."""
    if not os.path.isfile(SENT_LOG_CSV):
        return []
    with open(SENT_LOG_CSV, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))
