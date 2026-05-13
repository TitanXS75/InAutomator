"""
config/settings.py
Centralized configuration for the entire pipeline.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ────────────────────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER_NAME        = os.getenv("SENDER_NAME", "Candidate")

# ── Resume ─────────────────────────────────────────────────────
RESUME_PATH = os.getenv("RESUME_PATH", "assets/resume.pdf")

# ── Search Keywords ────────────────────────────────────────────
try:
    with open("keywords.txt", "r") as f:
        SEARCH_KEYWORDS = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    SEARCH_KEYWORDS = [
        "Java Developer hiring",
        "Full Stack Developer contract",
        "Python Developer recruiter",
    ]

# ── LinkedIn URLs ──────────────────────────────────────────────
LINKEDIN_LOGIN_URL  = "https://www.linkedin.com/login"
LINKEDIN_SEARCH_URL = "https://www.linkedin.com/search/results/content/?keywords={keyword}&datePosted=past-24h&sortBy=date"

# ── Timing / Delays (seconds) ──────────────────────────────────
PAGE_LOAD_DELAY   = float(os.getenv("PAGE_LOAD_DELAY", 3.0))
SCROLL_DELAY      = float(os.getenv("SCROLL_DELAY", 2.0))
ACTION_DELAY      = float(os.getenv("ACTION_DELAY", 1.5))
MAX_SCROLL_COUNT  = int(os.getenv("MAX_SCROLL_COUNT", 10))

# ── Email Settings ─────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
AUTO_SEND_EMAILS = os.getenv("AUTO_SEND_EMAILS", "True") == "True"

# ── File Paths ─────────────────────────────────────────────────
RECRUITERS_CSV = "data/recruiters.csv"
SENT_LOG_CSV   = "data/sent_log.csv"
LOG_FILE       = "logs/app.log"

# ── Email Template ─────────────────────────────────────────────
EMAIL_SUBJECT_TEMPLATE = "Application for {job_keyword} Role — {sender_name}"

EMAIL_BODY_TEMPLATE = """Dear {recruiter_name},

I came across your post about a {job_keyword} opportunity on LinkedIn and I am very interested in exploring this role further.

I have hands-on experience in {job_keyword} development and I am confident my background aligns well with what you are looking for. Please find my resume attached for your review.

I would love the opportunity to connect and discuss how I can contribute to your team or your client's requirements.

Looking forward to hearing from you.

Warm regards,
{sender_name}
{gmail_address}
"""
