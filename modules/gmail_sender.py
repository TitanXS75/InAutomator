"""
modules/gmail_sender.py

Sends personalized job application emails via Gmail SMTP.
Professional approach:
  - Uses App Password (no browser needed, no CAPTCHA)
  - Proper EHLO → STARTTLS → EHLO → LOGIN sequence
  - Retry logic on transient failures
  - Attaches resume as PDF
  - Logs every send to CSV for duplicate prevention
"""

import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from modules.email_composer import EmailComposer
from utils.logger import setup_logger
from utils.csv_handler import log_sent_email
from utils.duplicate_checker import DuplicateChecker
from config.settings import (
    SMTP_HOST, SMTP_PORT, RESUME_PATH, SENDER_NAME
)

logger = setup_logger()

_MAX_RETRIES    = 2
_SEND_DELAY_SEC = 4   # polite delay between sends


class GmailSender:
    """
    Sends bulk personalized emails via Gmail SMTP.
    Handles connection, retry, attachment, logging, and deduplication.
    """

    def __init__(self):
        self.composer    = EmailComposer()
        self.dup_checker = DuplicateChecker()
        self._smtp: smtplib.SMTP | None = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def send_bulk(self, recruiters: list[dict], stop_event=None) -> None:
        """
        Send one email per recruiter. Skips duplicates and retries on failure.

        Args:
            recruiters: list of dicts with keys: name, email, company, keyword
            stop_event: optional threading.Event to abort the process early
        """
        if not recruiters:
            logger.warning("No recruiters to email.")
            return

        # Dynamically fetch credentials so GUI updates take effect without restart
        gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
        gmail_pwd = os.environ.get("GMAIL_APP_PASSWORD", "")

        # Validate credentials before connecting
        if not gmail_addr or not gmail_pwd:
            logger.error("Gmail credentials missing. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env")
            return

        if not RESUME_PATH or not os.path.exists(RESUME_PATH):
            logger.warning(f"Resume not found at '{RESUME_PATH}'. Emails will be sent without attachment.")

        sent_count    = 0
        skipped_count = 0
        failed_count  = 0

        self._connect()
        if not self._smtp:
            logger.error("Could not connect to Gmail. Aborting send.")
            return

        for recruiter in recruiters:
            if stop_event and stop_event.is_set():
                logger.info("  [ABORT] Email sending stopped by user.")
                break

            email_addr = (recruiter.get("email") or "").strip().lower()
            if not email_addr or "@" not in email_addr:
                continue

            if self.dup_checker.already_sent(email_addr):
                logger.info(f"  [SKIP]  Already sent to {email_addr}")
                skipped_count += 1
                continue

            email_data = self.composer.compose(recruiter)
            success = self._send_with_retry(email_data)

            if success:
                self.dup_checker.mark_sent(email_addr)
                log_sent_email(email_addr, status="sent")
                sent_count += 1
                logger.info(f"  [SENT]  ✅ {email_addr} — '{email_data['subject']}'")
                time.sleep(_SEND_DELAY_SEC)
            else:
                log_sent_email(email_addr, status="failed")
                failed_count += 1
                logger.warning(f"  [FAIL]  ❌ {email_addr} — will retry next run")

        self._disconnect()

        logger.info("=" * 50)
        logger.info(f"Email run complete:")
        logger.info(f"  Sent:    {sent_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info(f"  Failed:  {failed_count}")
        logger.info("=" * 50)

    # ── Private Helpers ────────────────────────────────────────────────────────

    def _connect(self) -> None:
        """
        Establish SMTP connection to Gmail.
        Correct sequence: ehlo → starttls → ehlo → login
        """
        gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
        gmail_pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
        
        try:
            logger.info("Connecting to Gmail SMTP...")
            self._smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            self._smtp.ehlo()
            self._smtp.starttls()
            self._smtp.ehlo()   # Required again after STARTTLS
            self._smtp.login(gmail_addr, gmail_pwd)
            logger.info("Gmail SMTP connected and authenticated.")
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Gmail authentication FAILED. "
                "Ensure you are using an App Password (not your regular Gmail password). "
                "Enable 2FA then create an App Password at myaccount.google.com/apppasswords"
            )
            self._smtp = None
        except Exception as e:
            logger.error(f"SMTP connection error: {e}")
            self._smtp = None

    def _disconnect(self) -> None:
        """Gracefully close the SMTP session."""
        if self._smtp:
            try:
                self._smtp.quit()
                logger.info("Gmail SMTP connection closed.")
            except Exception:
                pass
            self._smtp = None

    def _send_with_retry(self, email_data: dict) -> bool:
        """
        Try to send a single email, with up to _MAX_RETRIES attempts.
        Reconnects if the SMTP session has gone stale between sends.
        """
        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                success = self._send_one(email_data)
                if success:
                    return True
            except smtplib.SMTPServerDisconnected:
                logger.warning(f"    SMTP disconnected. Reconnecting (attempt {attempt})...")
                self._connect()
            except Exception as e:
                logger.warning(f"    Send attempt {attempt} failed: {e}")

            if attempt <= _MAX_RETRIES:
                time.sleep(2)

        return False

    def _send_one(self, email_data: dict) -> bool:
        """
        Build and send one email with resume attached.

        Args:
            email_data: dict with keys: to, subject, body
        Returns:
            True if sent, False on any error.
        """
        if not self._smtp:
            return False

        gmail_addr = os.environ.get("GMAIL_ADDRESS", "")
        sender_name = os.environ.get("SENDER_NAME", "Candidate")

        msg = MIMEMultipart()
        msg["From"]    = f"{sender_name} <{gmail_addr}>"
        msg["To"]      = email_data["to"]
        msg["Subject"] = email_data["subject"]

        # Plain-text body
        msg.attach(MIMEText(email_data["body"], "plain", "utf-8"))

        # Resume attachment
        if RESUME_PATH and os.path.exists(RESUME_PATH):
            try:
                with open(RESUME_PATH, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(RESUME_PATH)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{filename}"'
                )
                msg.attach(part)
                logger.debug(f"    Resume attached: {filename}")
            except Exception as e:
                logger.warning(f"    Could not attach resume: {e}")

        self._smtp.sendmail(gmail_addr, email_data["to"], msg.as_string())
        return True
