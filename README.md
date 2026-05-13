# 🚀 LinkedIn Outreach Pro: Automated Recruiter Connect

**LinkedIn Outreach Pro** is a professional-grade automation tool designed to streamline your job search. It automates the tedious process of finding recruiter emails from LinkedIn posts and sending personalized job applications via Gmail.

## ✨ Key Features

- **Automated LinkedIn Login**: Securely saves your session so you don't have to log in every time.
- **Deep-Scan Extraction**: 
    - Scans recent LinkedIn posts (last 24 hours).
    - Automatically expands "See More" content to find hidden emails.
    - Deep-scans recruiter profiles and their recent activity feeds for contact details.
- **Intelligent Email Parsing**: Detects standard, spaced, and obfuscated emails (e.g., `hr [at] company [dot] com`).
- **Professional Dashboard (GUI)**:
    - **Home Tab**: Manage keywords and preview extracted emails.
    - **Credentials Tab**: Securely manage LinkedIn and Gmail settings.
    - **Control Panel**: Start/Stop automation and manually trigger email sending.
- **Smart Emailing**:
    - Automatic "Dear HR" fallback for unknown names.
    - Resume attachment support.
    - **Auto-Send Toggle**: Scrape and send in one click, or review before sending.
    - **Duplicate Prevention**: Never sends the same email twice to the same recruiter.

---

## 🛠️ Installation & Setup

### 1. Install Python
- **Requirement**: Python 3.10 or higher.
- **Windows**: Download from [python.org](https://www.python.org/downloads/windows/). During installation, **CRITICAL**: Check the box that says **"Add Python to PATH"**.
- **Verify**: Open your terminal/cmd and type:
  ```bash
  python --version
  ```

### 2. Prepare the Project
1. Clone or download this project folder.
2. Open your terminal inside the project folder.
3. (Optional but Recommended) Create a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # On Windows
   source venv/bin/activate  # On Mac/Linux
   ```

### 3. Install Dependencies
Install all required Python libraries and the automation browser:
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Gmail Security Setup
Standard Gmail passwords will NOT work. You must use an **App Password**:
1. Enable **2-Step Verification** on your Google Account.
2. Go to [App Passwords](https://myaccount.google.com/apppasswords).
3. Generate a new password for "Mail" and "Windows Computer".
4. Copy the **16-character code** (e.g., `abcd efgh ijkl mnop`).

---

## 🚀 How to Run

1. **Launch the Dashboard**:
   ```bash
   python gui.py
   ```
2. **Configure Credentials**:
   - Go to the **Credentials** tab.
   - Enter your LinkedIn email/password.
   - Enter your Gmail address and the **16-character App Password**.
   - Select your Resume PDF file.
   - Click **Save Settings**.
3. **Set Your Keywords**:
   - On the **Home** tab, enter keywords like `Java Developer, Contract`.
   - Click **✨ Enhance** to let the AI optimize your search terms.
4. **Start Automation**:
   - Click **Run Automation**.
   - A browser window will open. If it's your first time, you may need to solve a CAPTCHA.
   - The bot will scrape emails and display them in the **Found Emails** box.

---

## 📖 GUI Quick Guide

- **Found Emails Box**: You can manually edit this list! If you want to test with one specific email, delete everything else and just leave that one.
- **Send Mails Now**: Sends emails **only** to the addresses currently visible in the "Found Emails" box.
- **Stop Sending**: Aborts the manual email process immediately.
- **Logs Tab**: Watch the bot's "brain" in real-time to see what it's finding and doing.

---

## 📁 Project Structure

- `/modules`: Core logic for Login, Search, and Emailing.
- `/data`: Stores your `recruiters.csv` (found leads) and `sent_log.csv` (email history).
- `/logs`: Daily logs for troubleshooting.
- `gui.py`: The main entry point for the application.

---

## ⚠️ Important Note on Data
If you delete the contents of the `data/` folder:
1. **recruiters.csv**: You will lose all extracted email addresses and will need to run the scan again.
2. **sent_log.csv**: The bot will lose its memory of who it has already emailed and might send duplicate emails to the same people.
