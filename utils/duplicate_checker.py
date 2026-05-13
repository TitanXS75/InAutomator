"""
utils/duplicate_checker.py
Prevents sending duplicate emails to the same address.
Loads previously sent emails from sent_log.csv into memory at startup.
"""

from utils.csv_handler import load_sent_log


class DuplicateChecker:
    def __init__(self):
        """Load all previously sent email addresses into an in-memory set."""
        logs = load_sent_log()
        self._sent_emails: set[str] = {
            row["email"].strip().lower()
            for row in logs
            if row.get("status") == "sent"
        }

    def already_sent(self, email: str) -> bool:
        """Return True if this email was already sent to successfully."""
        return email.strip().lower() in self._sent_emails

    def mark_sent(self, email: str) -> None:
        """Mark an email as sent in the in-memory set."""
        self._sent_emails.add(email.strip().lower())
