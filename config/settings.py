"""
config/settings.py
Centralized configuration for the entire pipeline.
"""

import os
from dotenv import load_dotenv

# Project root (folder that contains gui.py, main.py, .env, data/, etc.)
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ENV_FILE = os.path.join(PROJECT_DIR, ".env")
KEYWORDS_FILE = os.path.join(PROJECT_DIR, "keywords.txt")
DATA_DIR = os.path.join(PROJECT_DIR, "data")
LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
USER_DATA_DIR = os.path.join(PROJECT_DIR, "user_data")

load_dotenv(dotenv_path=ENV_FILE)

# ── Credentials ────────────────────────────────────────────────
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER_NAME        = os.getenv("SENDER_NAME", "Candidate")

# ── Resume ─────────────────────────────────────────────────────
_resume_path = os.getenv("RESUME_PATH", os.path.join(PROJECT_DIR, "assets", "resume.pdf"))
# If RESUME_PATH in .env is relative (e.g. "assets/resume.pdf"), force it under project dir.
RESUME_PATH = _resume_path if os.path.isabs(_resume_path) else os.path.join(PROJECT_DIR, _resume_path)

# ── Search Keywords ────────────────────────────────────────────
try:
    with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
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
RECRUITERS_CSV = os.path.join(DATA_DIR, "recruiters.csv")
SENT_LOG_CSV   = os.path.join(DATA_DIR, "sent_log.csv")
LOG_FILE       = os.path.join(LOGS_DIR, "app.log")

# ── Email Template (GUI-editable files) ─────────────────────────
TEMPLATES_DIR = os.path.join(PROJECT_DIR, "templates")
EMAIL_SUBJECT_TEMPLATE_FILE = os.path.join(TEMPLATES_DIR, "email_subject_template.txt")
EMAIL_BODY_TEMPLATE_FILE = os.path.join(TEMPLATES_DIR, "email_body_template.txt")

_DEFAULT_EMAIL_SUBJECT_TEMPLATE = "Application for {job_keyword} Role — {sender_name}"

_DEFAULT_EMAIL_BODY_TEMPLATE = """Dear {recruiter_name},

I came across your post about a {job_keyword} opportunity on LinkedIn and I am very interested in exploring this role further.

I have hands-on experience in {job_keyword} development and I am confident my background aligns well with what you are looking for. Please find my resume attached for your review.

I would love the opportunity to connect and discuss how I can contribute to your team or your client's requirements.

Looking forward to hearing from you.

Warm regards,
{sender_name}
{gmail_address}
"""

def _read_template_file(path: str, default_value: str) -> str:
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        # If the file is locked or unreadable, fall back to defaults.
        pass
    return default_value

def get_email_subject_template() -> str:
    return _read_template_file(EMAIL_SUBJECT_TEMPLATE_FILE, _DEFAULT_EMAIL_SUBJECT_TEMPLATE)

def get_email_body_template() -> str:
    return _read_template_file(EMAIL_BODY_TEMPLATE_FILE, _DEFAULT_EMAIL_BODY_TEMPLATE)

# Backwards compatibility: constants available at import-time.
EMAIL_SUBJECT_TEMPLATE = get_email_subject_template()
EMAIL_BODY_TEMPLATE = get_email_body_template()
