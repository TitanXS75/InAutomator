"""
modules/email_composer.py
Generates personalized professional email content for each recruiter.
"""

from config.settings import (
    EMAIL_SUBJECT_TEMPLATE,
    EMAIL_BODY_TEMPLATE,
    SENDER_NAME,
    GMAIL_ADDRESS,
)


class EmailComposer:
    """Generates subject line and body for a recruiter outreach email."""

    def compose(self, recruiter: dict) -> dict:
        """
        Build email subject and body for a single recruiter.

        Args:
            recruiter: Dict with keys: name, email, company, keyword

        Returns:
            Dict with keys: to, subject, body
        """
        recruiter_name  = self._get_first_name(recruiter.get("name", "HR"))
        job_keyword     = recruiter.get("keyword", "Software Developer")
        recruiter_email = recruiter.get("email", "")

        subject = EMAIL_SUBJECT_TEMPLATE.format(
            job_keyword=job_keyword,
            sender_name=SENDER_NAME,
        )

        body = EMAIL_BODY_TEMPLATE.format(
            recruiter_name=recruiter_name,
            job_keyword=job_keyword,
            sender_name=SENDER_NAME,
            gmail_address=GMAIL_ADDRESS,
        )

        return {
            "to":      recruiter_email,
            "subject": subject,
            "body":    body,
        }

    @staticmethod
    def _get_first_name(full_name: str) -> str:
        """Extract first name from full name, fallback to 'HR'."""
        parts = full_name.strip().split()
        if not parts:
            return "HR"
        first = parts[0]
        if first.lower() in ["unknown", "recruiter"]:
            return "HR"
        return first
