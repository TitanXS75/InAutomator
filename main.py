"""
LinkedIn Job Search & Recruiter Outreach Automation System
Entry Point — Runs the complete 4-step pipeline.
"""

import sys
from utils.logger import setup_logger
from modules.linkedin_login import LinkedInLogin
from modules.job_search import JobSearch
from modules.gmail_sender import GmailSender
from config.settings import SEARCH_KEYWORDS, AUTO_SEND_EMAILS

logger = setup_logger()


def main():
    logger.info("=" * 60)
    logger.info("Starting LinkedIn Recruiter Outreach Automation")
    logger.info("=" * 60)

    # ── STEP 1: LinkedIn Login ──────────────────────────────────
    logger.info("[STEP 1] Logging into LinkedIn...")
    linkedin = LinkedInLogin()
    browser_page = linkedin.login()

    if not browser_page:
        logger.error("LinkedIn login failed. Exiting.")
        sys.exit(1)

    logger.info("[STEP 1] Login successful.")

    # ── STEP 2 & 3: Search + Extract Recruiter Data ─────────────
    logger.info("[STEP 2] Searching LinkedIn job posts...")
    searcher = JobSearch(browser_page)
    recruiters = []

    for keyword in SEARCH_KEYWORDS:
        logger.info(f"  Searching keyword: '{keyword}'")
        results = searcher.search_and_extract(keyword)
        recruiters.extend(results)
        logger.info(f"  Found {len(results)} recruiter(s) for '{keyword}'")

    linkedin.close()

    if not recruiters:
        logger.warning("No recruiter emails found. Nothing to send. Exiting.")
        sys.exit(0)

    logger.info(f"[STEP 3] Total recruiters extracted: {len(recruiters)}")

    # ── STEP 4: Send Emails via Gmail ───────────────────────────
    if AUTO_SEND_EMAILS:
        logger.info("[STEP 4] Sending emails via Gmail...")
        sender = GmailSender()
        sender.send_bulk(recruiters)
        
        logger.info("=" * 60)
        logger.info("Pipeline complete. Check data/sent_log.csv for results.")
        logger.info("=" * 60)
    else:
        logger.info("[STEP 4] Auto-send is DISABLED. Emails are saved in data/recruiters.csv.")
        logger.info("=" * 60)
        logger.info("Pipeline complete.")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
