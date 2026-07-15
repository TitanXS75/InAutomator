"""
modules/email_composer.py
Generates personalized professional email content for each recruiter.
"""

import os
import config.settings as settings


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

        subject_template = settings.get_email_subject_template()
        body_template = settings.get_email_body_template()

        # Read latest values from environment (GUI updates os.environ before running automation).
        sender_name = os.environ.get("SENDER_NAME", settings.SENDER_NAME)
        gmail_address = os.environ.get("GMAIL_ADDRESS", settings.GMAIL_ADDRESS)

        subject = subject_template.format(
            job_keyword=job_keyword,
            sender_name=sender_name,
        )

        body = body_template.format(
            recruiter_name=recruiter_name,
            job_keyword=job_keyword,
            sender_name=sender_name,
            gmail_address=gmail_address,
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
