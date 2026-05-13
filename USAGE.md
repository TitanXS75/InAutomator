# Usage Guide for LinkedIn Recruiter Outreach Automation

> **💡 Note: Customizing Your Email Template**
> The email subject and body templates are located in `config/settings.py`. You can open that file and edit `EMAIL_SUBJECT_TEMPLATE` and `EMAIL_BODY_TEMPLATE` manually to personalize your outreach message.

This guide explains how to properly set up and use the LinkedIn Job Search & Recruiter Outreach Automation System.

## Prerequisites
1. Python 3.10+ installed on your system.
2. Google Chrome (or Chromium browser) installed.
3. A LinkedIn account.
4. A Gmail account (with 2-Step Verification enabled to generate an App Password).

## Setup Steps

### 1. Configure the Environment Variables
1. Rename `env.example` to `.env` in the root directory.
2. Open `.env` and fill in your credentials:
   - `LINKEDIN_EMAIL`: Your LinkedIn login email.
   - `LINKEDIN_PASSWORD`: Your LinkedIn password.
   - `GMAIL_ADDRESS`: Your Gmail address.
   - `GMAIL_APP_PASSWORD`: Your 16-character App Password (go to your Google Account -> Security -> 2-Step Verification -> App Passwords).
   - `SENDER_NAME`: Your full name (used in email templates).
   - `RESUME_PATH`: Path to your resume, default is `assets/resume.pdf`.

### 2. Add Your Resume
Place your resume (in PDF format) inside the `assets/` directory and ensure it is named `resume.pdf` (or update `RESUME_PATH` in your `.env` file accordingly).

### 3. Install Dependencies
Open a terminal in the root directory and run:
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Search Keywords
Open `config/settings.py` and locate the `SEARCH_KEYWORDS` list. Update the keywords to match the roles you are looking for. For example:
```python
SEARCH_KEYWORDS = [
    "Python Developer hiring",
    "Data Engineer recruiter",
    "Software Engineer opportunity"
]
```
You can also customize the email template in the same file (`EMAIL_SUBJECT_TEMPLATE` and `EMAIL_BODY_TEMPLATE`).

## Running the Application

To execute the automation pipeline, simply run:
```bash
python main.py
```

### What Happens During Execution?
1. **LinkedIn Login**: The script will open a Chromium browser and log into LinkedIn using your credentials. (If LinkedIn asks for a 2FA/verification code, the browser will wait up to 60 seconds for you to enter it manually).
2. **Job Search & Extraction**: It will search for posts matching your keywords from the past 24 hours, scroll to find recruiter posts, and extract their names and email addresses.
3. **Data Logging**: Extracted recruiter details are saved in `data/recruiters.csv`.
4. **Email Outreach**: The script logs into your Gmail SMTP server and sends a personalized email with your resume attached to each recruiter. It prevents duplicate emails by checking `data/sent_log.csv`.

## Troubleshooting
- **LinkedIn Bot Detection**: If LinkedIn blocks the login, try running the script with a longer `PAGE_LOAD_DELAY` in `config/settings.py`.
- **Gmail Authentication Error**: Ensure you are using an **App Password** and not your main Gmail password.
- **Empty Extracted Data**: LinkedIn may have changed its HTML structure. Check the logs in `logs/app.log` and verify if the Playwright selectors in `modules/job_search.py` need updating.

## Note
Use this tool responsibly. Sending too many emails or performing excessive automated searches may lead to restrictions on your LinkedIn or Gmail accounts.
